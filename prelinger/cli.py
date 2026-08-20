"""prelinger — Prelinger Archive clip pipeline.

Typical flow:
  prelinger search "telepathy"        # grow data/candidates.csv + contact sheet
  open data/contact_sheet.html        # team screens candidates in the browser
  # add rows to data/clips.csv (identifier,start,end,role,...)
  prelinger fetch                     # proxies for every clips.csv identifier
  prelinger cut                       # normalized 1080p/24 ProRes clips
  prelinger matte                     # alpha assets (.mov + .webm)
  prelinger autotag                   # CLIP role suggestions into clips.csv
  # mark selects (status=select), then:
  prelinger fetch --tier master && prelinger cut && prelinger matte
  prelinger credits
"""

from pathlib import Path

import click
from rich.console import Console

from . import config
from .manifest import CLIP_FIELDS, read_rows, write_rows

console = Console()


@click.group(help=__doc__)
def cli():
    config.ensure_media_dirs()


@cli.command("search")
@click.argument("query")
@click.option("--limit", default=40, show_default=True)
@click.option("--sort", default="downloads desc", show_default=True,
              help="archive.org sort, e.g. 'downloads desc', 'date asc'.")
def search_cmd(query, limit, sort):
    """Search the Prelinger collection; append hits to candidates.csv."""
    from .search import build_contact_sheet, search

    found = search(query, limit, sort)
    build_contact_sheet()
    console.print(f"[green]{len(found)} hits[/] for {query!r} -> {config.CANDIDATES_CSV}")
    console.print(f"contact sheet: {config.CONTACT_SHEET}")


@cli.command("sheet")
def sheet_cmd():
    """Rebuild the contact sheet from candidates.csv."""
    from .search import build_contact_sheet

    build_contact_sheet()
    console.print(f"rebuilt {config.CONTACT_SHEET}")


@cli.command("fetch")
@click.argument("identifiers", nargs=-1)
@click.option("--tier", type=click.Choice(["proxy", "master"]), default="proxy",
              show_default=True)
@click.option("--all-candidates", is_flag=True,
              help="Fetch every candidates.csv identifier instead of clips.csv.")
@click.option("--sleep", "pause", default=3.0, show_default=True,
              help="Seconds to wait between items (be polite to archive.org).")
def fetch_cmd(identifiers, tier, all_candidates, pause):
    """Download derivatives. Default: proxies for clips.csv identifiers.

    --tier master downloads only rows whose status is 'select'.
    """
    from .fetch import fetch_item

    if identifiers:
        idents = list(identifiers)
    elif all_candidates:
        idents = [r["identifier"] for r in read_rows(config.CANDIDATES_CSV)]
    else:
        rows = read_rows(config.CLIPS_CSV)
        if tier == "master":
            rows = [r for r in rows if r.get("status", "").strip() == "select"]
        idents = sorted({r["identifier"] for r in rows if r.get("identifier")})
    if not idents:
        raise click.ClickException(
            "nothing to fetch — pass identifiers, fill data/clips.csv, or use --all-candidates"
        )
    import time

    for i, ident in enumerate(idents):
        if i:
            time.sleep(pause)
        try:
            path = fetch_item(ident, tier)
        except Exception as e:
            console.print(f"[red]{ident}: {type(e).__name__}[/] — retry later ({e})")
            continue
        if path is None:
            console.print(f"[yellow]{ident}: no {tier} derivative found[/]")
        else:
            console.print(f"[green]{ident}[/] -> {path}")


@cli.command("cut")
@click.option("--force", is_flag=True, help="Re-cut even if the clip exists.")
def cut_cmd(force):
    """Cut + normalize every clips.csv row with a downloaded source."""
    from .cut import cut_clip

    rows = read_rows(config.CLIPS_CSV)
    if not rows:
        raise click.ClickException(f"no rows in {config.CLIPS_CSV}")
    for row in rows:
        if not (row.get("identifier") and row.get("start") and row.get("end")):
            continue
        try:
            cut_clip(row, force=force)
            console.print(f"[green]cut[/] {row['clip_path']} ({row['cut_tier']})")
        except FileNotFoundError as e:
            console.print(f"[yellow]skip[/] {e}")
    write_rows(config.CLIPS_CSV, rows, CLIP_FIELDS)


@cli.command("matte")
@click.option("--force", is_flag=True)
def matte_cmd(force):
    """Matte cut clips into alpha assets (.mov + .webm). matte=no -> passthrough."""
    from .matte import matte_clip, passthrough_clip, to_webm

    rows = read_rows(config.CLIPS_CSV)
    done = 0
    for row in rows:
        clip = row.get("clip_path")
        if not clip:
            continue
        wants_alpha = row.get("matte", "").strip().lower() not in ("no", "false", "0")
        out = config.ASSETS / (Path(clip).stem + ".mov")
        if out.exists() and not force:
            continue
        out = matte_clip(clip) if wants_alpha else passthrough_clip(clip)
        webm = to_webm(out, alpha=wants_alpha)
        console.print(f"[green]asset[/] {out} + {webm.name}")
        done += 1
    console.print(f"{done} asset(s) written to {config.ASSETS}")


@cli.command("autotag")
def autotag_cmd():
    """Write CLIP role suggestions into clips.csv (suggested_roles column)."""
    from .autotag import suggest_roles

    rows = read_rows(config.CLIPS_CSV)
    for row in rows:
        if row.get("clip_path") and not row.get("suggested_roles"):
            row["suggested_roles"] = suggest_roles(row["clip_path"])
            console.print(f"{row['identifier']} [{row['start']}-{row['end']}]: "
                          f"{row['suggested_roles']}")
    write_rows(config.CLIPS_CSV, rows, CLIP_FIELDS)


@cli.command("credits")
def credits_cmd():
    """Generate data/credits.md from clips.csv."""
    from .credits import build_credits

    n = build_credits()
    console.print(f"[green]{n} source films[/] -> {config.CREDITS_MD}")
