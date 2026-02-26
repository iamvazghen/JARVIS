import os
import fnmatch


def spec():
    return {
        "name": "file_search",
        "description": "Search for files by name substring and/or glob pattern under a directory.",
        "args": {"root": "string", "name_contains": "string", "glob": "string", "max_results": "number"},
    }


def run(*, assistant=None, wolfram_fn=None, root=".", name_contains="", glob="*", max_results=25):
    try:
        max_results = int(max_results)
    except Exception:
        max_results = 25
    max_results = max(1, min(200, max_results))

    root = root or "."
    name_contains = (name_contains or "").lower()
    glob = glob or "*"

    results = []
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if name_contains and name_contains not in filename.lower():
                continue
            if glob and not fnmatch.fnmatch(filename, glob):
                continue
            results.append(os.path.join(dirpath, filename))
            if len(results) >= max_results:
                return results
    return results

