#!/usr/bin/env python
import os
import sys
import shutil
import json
import urllib
import htmlmin
import frontmatter
import yaml
from markdown2 import markdown
from jinja2 import Environment, FileSystemLoader
from rcssmin import cssmin


class Config:
    """The config class"""

    def __init__(self, working_dir, config_file="harmonique.yml"):
        self.working_dir = working_dir
        self.config = {
            "source_path": "source",
            "output_path": "output",
            "theme_path": "theme",
            "toc_path": "toc.json",
            "markdown2_extras": [
                "code-friendly",
                "fenced-code-blocks",
                "target-blank-links",
                "metadata",
            ],
        }
        config_path = os.path.join(working_dir, config_file)
        if os.path.exists(config_path):
            with open(config_path, "r") as cfile:
                self.config.update(yaml.load(cfile))

    def _join_path(self, key):
        return os.path.join(self.working_dir, self.config[key])

    def __getattr__(self, name):
        if name in self.config:
            if name.endswith("_path"):
                return self._join_path(name)
            return self.config[name]
        raise AttributeError(f"The config key '{name}' does not exist.")


def find_input_file_names(config):
    """
    Return a list of all markdown files from the source directory
    """
    try:
        files = os.listdir(config.source_path)
        return filter(lambda fname: fname.endswith(".md"), files)
    except FileNotFoundError:
        return []


def get_io_path_map(config, input_file_names):
    """
    Return a map of <input_file_path>:<output_file_path>
    Both key and values are relative filepaths
    """
    paths = {}
    for name in input_file_names:
        input_path = os.path.join(config.source_path, name)

        output_md = os.path.join(config.output_path, name)
        output_dir, _ = os.path.splitext(output_md)
        output_path = os.path.join(output_dir, "index.html")

        paths[input_path] = output_path
    return paths


def get_convertible_files(config, io_path_map):
    """
    Return a dict of input:output paths
    """
    # if there is no output directory then everything in the source
    # directory is fresh
    if not os.path.exists(config.output_path):
        return io_path_map

    fresh_path_map = {}

    for input_path, output_path in io_path_map.items():
        if not os.path.exists(output_path):
            fresh_path_map[input_path] = output_path
            continue

        source_mtime = os.path.getmtime(input_path)
        dest_mtime = os.path.getmtime(output_path)

        if source_mtime > dest_mtime:
            fresh_path_map[input_path] = output_path
    return fresh_path_map


def read_file_content(input_path):
    with open(input_path, "r") as input_file:
        return input_file.read()


def parse_file(config, input_path, output_path):
    """
    Open, read and parse a input markdown file and return
    a dict with the parsed information.
    """
    text = read_file_content(input_path)
    html = markdown(text, extras=config.markdown2_extras)

    meta = dict(frontmatter.loads(text))

    if not meta:
        return None

    document = {
        # default properties of a document
        "date": None,
        "location": None,
        "title": None,
        "description": None,
        "draft": True,
        "code": False,
        # end of defaults
        "text": text,
        "html": html,
        "input_file_name": os.path.split(input_path)[-1],
        "input_path": input_path,
        "output_path": output_path,
        "output_dir": os.path.split(output_path)[0],
    }
    document.update(meta)
    return document


def get_parsed_docs(config, path_map):
    skipped = []
    documents = []

    for input_path, output_path in path_map.items():
        document = parse_file(config, input_path, output_path)

        if document:
            documents.append(document)
        else:
            skipped.append(input_path)

    sorted_docs = sorted(documents, key=lambda d: d["date"], reverse=True)
    return sorted_docs, skipped


def get_css_chunks(config):
    css_path = os.path.join(config.theme_path, "css")
    css_chunks = {}

    if not os.path.exists(css_path):
        return css_chunks

    for filename in os.listdir(css_path):
        if not filename.endswith(".css"):
            continue
        filepath = os.path.join(css_path, filename)
        with open(filepath) as css_file:
            css_chunks[filename] = cssmin(css_file.read())
    return css_chunks


def publish_document(config, document):
    if not os.path.exists(document["output_dir"]):
        os.makedirs(document["output_dir"])

    with open(document["output_path"], "w") as output:
        output.write(document["page"])


def unpublish_document(config, document):
    if os.path.exists(document["output_dir"]):
        shutil.rmtree(document["output_dir"])


def get_theme(config):
    template_path = os.path.join(config.theme_path, "templates")
    env = Environment(loader=FileSystemLoader(template_path))
    css_chunks = get_css_chunks(config)

    return {
        "env": env,
        "template_path": template_path,
        "detail_template": env.get_template("detail.html"),
        "index_template": env.get_template("index.html"),
        "css": "\n".join(css_chunks.values()),
        "css_chunks": css_chunks,
    }


def build_site_index(config, theme, toc, build_mode):
    context = {
        "object_list": toc,
        "is_index": True,
        "theme": theme,
        "config": config,
        "build_mode": build_mode,
    }
    index_path = os.path.join(config.output_path, "index.html")
    with open(index_path, "w") as fi:
        fi.write(htmlmin.minify(theme["index_template"].render(context)))


def get_toc(config, published, unpublished):
    try:
        with open(config.toc_path, "r") as toc_file:
            toc = json.load(toc_file)
    except FileNotFoundError:
        toc = {}

    for doc in unpublished:
        toc.pop(doc["input_file_name"], None)

    for doc in published:
        url = os.path.split(doc["output_dir"])[-1] + "/"

        toc[doc["input_file_name"]] = {
            "title": doc["title"],
            "date": doc["date"].isoformat(),
            "draft": doc["draft"],
            "url": url,
        }

    with open(config.toc_path, "w") as toc_file:
        json.dump(toc, toc_file, indent=4)
    return toc


def build_content(config, docs, theme, build_mode):
    published = []
    unpublished = []

    for doc in docs:
        context = {
            "theme": theme,
            "doc": doc,
            "config": config,
            "build_mode": build_mode,
        }
        doc["page"] = htmlmin.minify(theme["detail_template"].render(context))

        if doc["draft"]:
            unpublish_document(config, doc)
            unpublished.append(doc)
        else:
            publish_document(config, doc)
            published.append(doc)
    return published, unpublished


def build_site(config, build_mode):
    file_names = find_input_file_names(config)
    io_path_map = get_io_path_map(config, file_names)

    if not io_path_map:
        return

    if os.path.exists(config.toc_path):
        path_map = get_convertible_files(config, io_path_map)
    else:
        path_map = io_path_map

    docs, skipped = get_parsed_docs(config, path_map)
    theme = get_theme(config)
    published, unpublished = build_content(config, docs, theme, build_mode)
    toc = get_toc(config, published, unpublished).values()
    build_site_index(config, theme, toc, build_mode)

    return {
        "published": published,
        "unpublished": unpublished,
        "skipped": skipped,
    }


def watch_and_build(config):
    pass


def main():
    if len(sys.argv) > 1:
        build_mode = sys.argv[1]
    else:
        build_mode = "production"

    if build_mode not in ["development", "production"]:
        print(f"Invalid build mode {build_mode}")
        sys.exit(1)
    print(f"Starting build in {build_mode}")

    config = Config(os.getcwd())
    report = build_site(config, build_mode)

    if not report:
        print("Nothing to build...")
        return

    for k, v in report.items():
        print(f"{k}: {len(v)}")


if __name__ == "__main__":
    main()
