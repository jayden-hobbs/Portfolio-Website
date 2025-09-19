#!/usr/bin/env python3
"""
Static portfolio manager and builder with free-form dates and flexible links.

Commands:
  list
  add --slug SLUG --title TITLE [--summary TEXT] [--date TEXT] [--tags t1 t2]
      [--image /assets/slug/card.jpg] [--hero /assets/slug/hero.jpg]
  edit --index N [--slug SLUG] [--title TITLE] [--summary TEXT] [--date TEXT]
       [--tags t1 t2] [--image PATH] [--hero PATH]
  delete --index N
  attach --index N --name NAME --url URL
  link-add --index N --name NAME --url URL
  link-del --index N --link-index K
  build

Layout (relative to this script):
  projects.json  : project metadata
  templates/     : index.html, project.html (Jinja2)
  content/       : {slug}.md write-ups
  projects/      : output {slug}.html
  assets/        : images/files (referenced in JSON)

Requirements:
  pip install jinja2 markdown
"""

import argparse
import json
import os
import sys
from typing import List, Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    import markdown  # type: ignore
except ImportError:
    markdown = None

# Paths
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ROOT, "projects.json")
TPL_DIR = os.path.join(ROOT, "templates")
OUT_DIR = ROOT                           # index.html at root
PROJECTS_DIR = os.path.join(ROOT, "projects")
CONTENT_DIR = os.path.join(ROOT, "content")

# ------------- Utilities -------------

def load_data() -> List[Dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: List[Dict[str, Any]]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_dirs() -> None:
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    os.makedirs(CONTENT_DIR, exist_ok=True)
    os.makedirs(TPL_DIR, exist_ok=True)

def md_to_html(slug: str) -> str:
    path = os.path.join(CONTENT_DIR, f"{slug}.md")
    if os.path.exists(path) and markdown:
        with open(path, "r", encoding="utf-8") as f:
            return markdown.markdown(
                f.read(),
                extensions=["fenced_code", "codehilite", "tables", "toc", "sane_lists"],
                output_format="html5",
            )
    return "<p>No write-up yet.</p>"

def get_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TPL_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

def validate_index(idx: int, data: List[Dict[str, Any]]) -> None:
    if idx < 0 or idx >= len(data):
        print("Error: invalid index")
        sys.exit(1)

# ------------- Commands -------------

def cmd_list(_args: argparse.Namespace) -> None:
    data = load_data()
    if not data:
        print("No projects yet.")
        return
    for i, p in enumerate(data):
        tags = ", ".join(p.get("tags", []))
        date = p.get("date", "")
        date_sfx = f" — {date}" if date else ""
        print(f"[{i}] {p.get('slug','?'):20} — {p.get('title','Untitled')}{date_sfx} [{tags}]")

def cmd_add(args: argparse.Namespace) -> None:
    data = load_data()
    if any(x.get("slug") == args.slug for x in data):
        print("Error: slug already exists")
        sys.exit(1)
    item: Dict[str, Any] = {
        "slug": args.slug,
        "title": args.title,
        "summary": args.summary or "",
        "date": args.date or "",          # free-form text
        "tags": args.tags or [],
        "image": args.image or "",
        "hero": args.hero or "",
        "attachments": [],
        "links": [],                       # flexible list of {name,url}
    }
    data.append(item)
    save_data(data)

    # Seed markdown file if missing
    os.makedirs(CONTENT_DIR, exist_ok=True)
    md_path = os.path.join(CONTENT_DIR, f"{args.slug}.md")
    if not os.path.exists(md_path):
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {args.title}\n\nWrite-up coming soon.\n")

    print(f"Added project '{args.slug}'")

def cmd_edit(args: argparse.Namespace) -> None:
    data = load_data()
    validate_index(args.index, data)
    p = data[args.index]

    # Update scalar fields if provided
    for key in ["slug", "title", "summary", "date", "image", "hero"]:
        val = getattr(args, key)
        if val is not None:
            p[key] = val

    # Tags replacement if provided
    if args.tags is not None:
        p["tags"] = args.tags

    save_data(data)
    print(f"Edited [{args.index}] -> slug='{p.get('slug')}'")

def cmd_delete(args: argparse.Namespace) -> None:
    data = load_data()
    validate_index(args.index, data)
    p = data.pop(args.index)
    save_data(data)

    # Remove generated HTML if exists
    html_path = os.path.join(PROJECTS_DIR, f"{p.get('slug')}.html")
    if os.path.exists(html_path):
        try:
            os.remove(html_path)
        except OSError:
            pass
    print(f"Deleted '{p.get('slug')}'")

def cmd_attach(args: argparse.Namespace) -> None:
    data = load_data()
    validate_index(args.index, data)
    p = data[args.index]
    p.setdefault("attachments", [])
    p["attachments"].append({"name": args.name, "url": args.url})
    save_data(data)
    print(f"Attached '{args.name}' to '{p.get('slug')}'")

def cmd_link_add(args: argparse.Namespace) -> None:
    data = load_data()
    validate_index(args.index, data)
    p = data[args.index]
    p.setdefault("links", [])
    p["links"].append({"name": args.name, "url": args.url})
    save_data(data)
    print(f"Added link '{args.name}' to '{p.get('slug')}'")

def cmd_link_del(args: argparse.Namespace) -> None:
    data = load_data()
    validate_index(args.index, data)
    p = data[args.index]
    links = p.get("links", [])
    if args.link_index < 0 or args.link_index >= len(links):
        print("Error: invalid link_index")
        sys.exit(1)
    removed = links.pop(args.link_index)
    save_data(data)
    print(f"Removed link '{removed.get('name','')}' from '{p.get('slug')}'")

def cmd_build(_args: argparse.Namespace) -> None:
    ensure_dirs()
    env = get_env()

    try:
        tpl_index = env.get_template("index.html")
        tpl_project = env.get_template("project.html")
    except Exception as e:
        print(f"Template error: {e}")
        sys.exit(1)

    projects = load_data()

    # Render index.html at root
    idx_html = tpl_index.render(projects=projects)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(idx_html)

    # Render each project's page
    count = 0
    for p in projects:
        slug = p.get("slug")
        if not slug:
            print(f"Skipping project with no slug: {p}")
            continue
        body_html = md_to_html(slug)
        html = tpl_project.render(project=p, body_html=body_html)
        out_path = os.path.join(PROJECTS_DIR, f"{slug}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        count += 1

    print(f"Built index and {count} project page(s).")

# ------------- CLI -------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Manage and build a static cybersecurity portfolio")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List projects").set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="Add a new project")
    p_add.add_argument("--slug", required=True)
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--summary")
    p_add.add_argument("--date", help="Free-form date text, e.g., 'Sep 2025'")
    p_add.add_argument("--tags", nargs="*")
    p_add.add_argument("--image", help="Card preview image path, e.g., /assets/slug/card.jpg")
    p_add.add_argument("--hero", help="Hero image path, e.g., /assets/slug/hero.jpg")
    p_add.set_defaults(func=cmd_add)

    p_edit = sub.add_parser("edit", help="Edit an existing project by index")
    p_edit.add_argument("--index", type=int, required=True)
    p_edit.add_argument("--slug")
    p_edit.add_argument("--title")
    p_edit.add_argument("--summary")
    p_edit.add_argument("--date")
    p_edit.add_argument("--tags", nargs="*")
    p_edit.add_argument("--image")
    p_edit.add_argument("--hero")
    p_edit.set_defaults(func=cmd_edit)

    p_del = sub.add_parser("delete", help="Delete a project by index")
    p_del.add_argument("--index", type=int, required=True)
    p_del.set_defaults(func=cmd_delete)

    p_att = sub.add_parser("attach", help="Add an attachment to a project by index")
    p_att.add_argument("--index", type=int, required=True)
    p_att.add_argument("--name", required=True)
    p_att.add_argument("--url", required=True)
    p_att.set_defaults(func=cmd_attach)

    link_add = sub.add_parser("link-add", help="Add a named link to a project by index")
    link_add.add_argument("--index", type=int, required=True)
    link_add.add_argument("--name", required=True)
    link_add.add_argument("--url", required=True)
    link_add.set_defaults(func=cmd_link_add)

    link_del = sub.add_parser("link-del", help="Delete a link by position from a project")
    link_del.add_argument("--index", type=int, required=True)
    link_del.add_argument("--link-index", type=int, required=True)
    link_del.set_defaults(func=cmd_link_del)

    p_build = sub.add_parser("build", help="Render index.html and project pages to /projects")
    p_build.set_defaults(func=cmd_build)

    return ap

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
