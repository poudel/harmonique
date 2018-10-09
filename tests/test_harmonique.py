import os
from harmonique import (
    find_input_file_names,
    get_io_path_map,
    get_convertible_files,
    read_file_content,
    parse_file,
    get_parsed_docs,
)


def test_asdf():
    print(os.path.curdir)
    assert 0, os.path.curdir
