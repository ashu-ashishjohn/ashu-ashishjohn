# Profile art maintenance

This repository is the special public profile repository for `ashu-ashishjohn`.
The README appears on the GitHub profile automatically.

The scheduled workflow updates `contributions.json` and `contrib-heatmap.svg`
daily, using GitHub's public contribution calendar. It uses only Python's
standard library and the repository-scoped GitHub Actions token. No personal
access token or third-party statistics service is needed.

To refresh the graph locally with Python 3.12:

```sh
python profile_art.py
```

To render a saved snapshot without a network request:

```sh
python profile_art.py --offline
```

The profile card and ASCII avatar are updated only when details or the avatar
change. To rebuild the profile card, edit the rows in `render_info` and run:

```sh
python profile_art.py --offline --info
```

To create ASCII art from your own avatar image, install Pillow locally and run:

```sh
python -m pip install Pillow
python profile_art.py --offline --avatar avatar.png
```

Use `--static` to create a fully visible frame for preview. Re-run without that
flag before committing the animated assets. Existing text and images remain
visible in clients without animation support. Animations play once.

If GitHub changes the calendar markup, the fetcher fails rather than inventing
counts or replacing the last successful snapshot with empty data. Inspect the
failed run in the Actions tab before updating the parser.

The SVGs and generator were written specifically for this profile. The layout
was inspired by Avi Vashishta's animated README guide, linked in the README.
