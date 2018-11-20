#!/usr/bin/env python
import os
import sys
import re
import logging
import shutil
from functools import partial
from http.server import SimpleHTTPRequestHandler, test as http_server

import htmlmin
import frontmatter
import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
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
            "site_url": "http://example.com/",
            "server_port": 8888,
            "server_bind": "127.0.0.1",
            # interlink pattern and url template respectively
            "interlink_pattern": r"\[il:(?P<slug>.+)\][ ]{0,3}\[(?P<anchor>.+)\]",
            "interlink_url_template": "<a href='{url}'>{anchor}</a>",
            "markdown2_extras": [
                "code-friendly",
                "fenced-code-blocks",
                "target-blank-links",
                "metadata",
                "header-ids",
                "toc",
                "footnotes",
                "tables",
                "cuddled-lists",
            ],
        }
        config_path = os.path.join(working_dir, config_file)
        if os.path.exists(config_path):
            with open(config_path, "r") as cfile:
                self.config.update(yaml.load(cfile))

        # compile and cache the interlink regex object here
        self.config["interlink_re"] = re.compile(
            self.config["interlink_pattern"]
        )

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
        output_md = os.path.join(config.output_path, name)
        output_dir, _ = os.path.splitext(output_md)
        output_path = os.path.join(output_dir, "index.html")

        input_path = os.path.join(config.source_path, name)
        paths[input_path] = output_path
    return paths


def read_file_content(input_path):
    with open(input_path, "r") as input_file:
        return input_file.read()


def interlink(config, text):
    """
    Create interlinks between articles
    """

    def interlink_sub(match):
        slug, anchor = match.groups()
        splitted = slug.split("#")
        joins = [f"/{slug}/"]
        if len(splitted) > 1:
            joins.append(splitted[-1])
        url = "#".join(joins)
        return config.interlink_url_template.format(url=url, anchor=anchor)

    return config.interlink_re.sub(interlink_sub, text)


def parse_file(config, input_path, output_path):
    """
    Open, read and parse a input markdown file and return
    a dict with the parsed information.
    """
    text = read_file_content(input_path)
    text = interlink(config, text)
    html = markdown(text, extras=config.markdown2_extras)

    meta = dict(frontmatter.loads(text))
    if not meta:
        return None

    output_dir = os.path.split(output_path)[0]
    url = os.path.split(output_dir)[-1] + "/"
    canonical_url = config.site_url + url
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
        "output_dir": output_dir,
        "url": url,
        "canonical_url": canonical_url,
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
        "sitemaps_template": env.get_template("sitemaps.txt"),
        "css": "\n".join(css_chunks.values()),
        "css_chunks": css_chunks,
    }


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

        if build_mode == "dev" or not doc["draft"]:
            publish_document(config, doc)
            published.append(doc)
        else:
            unpublish_document(config, doc)
            unpublished.append(doc)
    return published, unpublished


def build_site_index(config, theme, docs, build_mode):
    context = {
        "object_list": docs,
        "theme": theme,
        "config": config,
        "build_mode": build_mode,
    }
    path = os.path.join(config.output_path, "index.html")
    with open(path, "w") as fi:
        fi.write(htmlmin.minify(theme["index_template"].render(context)))


def build_sitemaps(config, theme, docs):
    context = {"object_list": docs}
    path = os.path.join(config.output_path, "sitemaps.xml")
    with open(path, "w") as fi:
        fi.write(theme["sitemaps_template"].render(context))


def build_site(config, build_mode):
    file_names = find_input_file_names(config)
    path_map = get_io_path_map(config, file_names)

    if not path_map:
        return

    docs, skipped = get_parsed_docs(config, path_map)
    theme = get_theme(config)
    published, unpublished = build_content(config, docs, theme, build_mode)
    build_site_index(config, theme, published, build_mode)
    build_sitemaps(config, theme, published)

    return {
        "published": published,
        "unpublished": unpublished,
        "skipped": skipped,
    }


def run_http_server(config):
    handler = partial(SimpleHTTPRequestHandler, directory=config.output_path)
    http_server(
        HandlerClass=handler, port=config.server_port, bind=config.server_bind
    )


def just_do_build(config, build_mode):
    report = build_site(config, build_mode)

    if not report:
        logging.error("Nothing to build at all.")
        return

    for k in ["published", "unpublished", "skipped"]:
        count = len(report[k])
        logging.info("%s: %s", k, count)


def watch_and_build(config, build_mode):
    just_do_build(config, build_mode)

    class EventHandler(FileSystemEventHandler):
        def on_any_event(self, event):
            logging.info("Changed %s", os.path.relpath(event.src_path))
            if not event.is_directory:
                build_site(config, build_mode)

    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, config.source_path)
    observer.schedule(event_handler, config.theme_path, recursive=True)
    observer.start()
    run_http_server(config)
    observer.stop()
    observer.join()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    serve = False
    if len(sys.argv) > 2:
        if sys.argv[2].lower() == "serve":
            serve = True

    if len(sys.argv) > 1:
        build_mode = sys.argv[1].lower()
    else:
        build_mode = "prod"

    if build_mode not in ["dev", "prod"]:
        logging.info("Invalid build mode %s", build_mode)
        sys.exit(1)

    config = Config(os.getcwd())

    if not os.path.exists(config.source_path):
        logging.error("Source path: '%s' does not exist.", config.source_path)
        logging.error("Make sure you're inside the right directory.")
        sys.exit(1)

    logging.info("Starting build in %s", build_mode)

    if serve:
        watch_and_build(config, build_mode)
    else:
        just_do_build(config, build_mode)


if __name__ == "__main__":
    main()
