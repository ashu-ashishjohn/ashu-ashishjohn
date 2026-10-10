"""Generate the profile's SVG art using real public GitHub contributions.

The scheduled path uses only Python's standard library. Pillow is needed only
when recreating the ASCII avatar locally with --avatar path/to/image.png.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
USERNAME = 'ashu-ashishjohn'
SOURCE = f'https://github.com/users/{USERNAME}/contributions'
BG, PANEL, LINE = '#0d1117', '#161b22', '#30363d'
TEXT, MUTED, BLUE, GREEN = '#d1d7e0', '#8b949e', '#79c0ff', '#3fb950'
PALETTE = ['#21262d', '#0e4429', '#006d32', '#26a641', '#39d353']
FONT = 'Cascadia Code, SFMono-Regular, Consolas, Liberation Mono, monospace'


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.days = []
        self.tooltips = {}
        self.tooltip_target = None
        self.tooltip_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('td', 'rect') and attrs.get('data-date'):
            self.days.append({
                'date': attrs['data-date'], 'id': attrs.get('id', ''),
                'level': int(attrs.get('data-level', '0')),
                'count': int(attrs['data-count']) if 'data-count' in attrs else None,
            })
        if tag == 'tool-tip':
            self.tooltip_target = attrs.get('for')
            self.tooltip_parts = []

    def handle_data(self, data):
        if self.tooltip_target is not None:
            self.tooltip_parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.tooltip_target is not None:
            self.tooltips[self.tooltip_target] = ''.join(self.tooltip_parts).strip()
            self.tooltip_target = None

    def records(self):
        if not self.days:
            raise ValueError('GitHub returned no calendar cells; previous data will be kept.')
        records = {}
        for day in self.days:
            count = day['count']
            if count is None:
                label = self.tooltips.get(day['id'], '')
                if re.match(r'No contributions\b', label, re.I):
                    count = 0
                else:
                    match = re.search(r'([\d,]+) contributions?\b', label, re.I)
                    if not match:
                        raise ValueError(f"Missing exact contribution count for {day['date']}")
                    count = int(match.group(1).replace(',', ''))
            date.fromisoformat(day['date'])
            if count < 0 or not 0 <= day['level'] <= 4:
                raise ValueError('Invalid contribution record')
            records[day['date']] = {'date':day['date'], 'count':count, 'level':day['level']}
        days = sorted(records.values(), key=lambda d:d['date'])
        if not 300 <= len(days) <= 380:
            raise ValueError(f'Unexpected calendar length: {len(days)}')
        dates = [date.fromisoformat(d['date']) for d in days]
        if any(b-a != timedelta(days=1) for a,b in zip(dates, dates[1:])):
            raise ValueError('Contribution calendar has missing days')
        return days


def fetch_calendar():
    request = urllib.request.Request(SOURCE, headers={
        'User-Agent':'ashu-ashishjohn-profile-art/1.0',
        'Accept':'text/html',
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                parser = CalendarParser()
                parser.feed(response.read().decode('utf-8'))
            days = parser.records()
            return {
                'schema_version':1, 'username':USERNAME, 'source':SOURCE,
                'updated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'days':days,
            }
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def svg_start(width, height, title, description):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">',
        f'<title id="title">{escape(title)}</title><desc id="description">{escape(description)}</desc>',
        f'<rect width="{width}" height="{height}" rx="12" fill="{BG}"/>']


def text(x, y, value, size=14, color=TEXT, extra=''):
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{color}" {extra}>{escape(str(value))}</text>'


def save_svg(name, parts):
    (ROOT/name).write_text('\n'.join(parts+['</svg>'])+'\n', encoding='utf-8')


def render_heatmap(data, static=False):
    if data['username'] != USERNAME:
        raise ValueError('Contribution data belongs to a different account')
    days = data['days']
    start = date.fromisoformat(days[0]['date'])
    start -= timedelta(days=(start.weekday()+1) % 7)
    end = date.fromisoformat(days[-1]['date'])
    weeks = (end-start).days//7+1
    width, height = 860, 262
    parts = svg_start(width,height,'Ashish John public GitHub contributions',
        f"{sum(d['count'] for d in days)} real public contributions from {days[0]['date']} to {days[-1]['date']}.")
    parts += [text(24,34,'ashish@github:~$ contributions --public',15,BLUE),
        f'<line x1="24" y1="50" x2="836" y2="50" stroke="{LINE}"/>']
    if not static:
        parts.append('<style>@keyframes reveal{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}.day{animation:reveal .22s both}@media(prefers-reduced-motion:reduce){.day{animation:none}}</style>')
    size, gap = 11, 3
    pitch = size+gap
    grid_x = (width-weeks*pitch+gap)/2+10
    grid_y = 88
    for row,label in [(1,'Mon'),(3,'Wed'),(5,'Fri')]:
        parts.append(text(grid_x-34,grid_y+row*pitch+9,label,10,MUTED))
    months = set()
    for d in days:
        day = date.fromisoformat(d['date'])
        week, weekday = (day-start).days//7,(day.weekday()+1)%7
        x,y = grid_x+week*pitch,grid_y+weekday*pitch
        if day.day <= 7 and (day.year,day.month) not in months:
            parts.append(text(x,grid_y-12,day.strftime('%b'),10,MUTED))
            months.add((day.year,day.month))
        color = PALETTE[min(4,max(0,d['level']))]
        animation = f' class="day" style="animation-delay:{(week+weekday)*.018:.3f}s"' if not static else ''
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{size}" height="{size}" rx="2" fill="{color}"{animation}><title>{d["date"]}: {d["count"]} contributions</title></rect>')
    total = sum(d['count'] for d in days)
    parts += [text(24,220,f'{total:,} public contributions in the last year',13,TEXT),
        text(24,243,'Updated '+data['updated_at'][:10]+' UTC',11,MUTED),
        text(685,226,'Less',10,MUTED)]
    for i,color in enumerate(PALETTE):
        parts.append(f'<rect x="{720+i*15}" y="217" width="11" height="11" rx="2" fill="{color}"/>')
    parts.append(text(800,226,'More',10,MUTED))
    save_svg('contrib-heatmap.svg',parts)


def render_info(static=False):
    parts = svg_start(490,390,'Ashish John .NET Backend Developer',
        '.NET, ASP.NET and VB.NET intermediate to advanced; SQL intermediate; Angular beginner with page and table creation and API integration; AI with .NET beginner.')
    parts += [text(24,35,'ashish@github:~$ whoami',14,BLUE),
        f'<line x1="24" y1="51" x2="466" y2="51" stroke="{LINE}"/>',
        text(24,86,'Ashish John',25,TEXT),text(24,113,'.NET Backend Developer',16,BLUE)]
    if not static:
        parts.append('<style>@keyframes print{from{opacity:0}to{opacity:1}}.row{animation:print .2s both}@media(prefers-reduced-motion:reduce){.row{animation:none}}</style>')
    rows = [
        ('Focus','C# / ASP.NET / REST APIs'),
        ('.NET','Intermediate to advanced'),
        ('VB.NET','Intermediate to advanced'),
        ('SQL','Intermediate'),
        ('Angular','Beginner / practical experience'),
        ('  work','Pages / tables / API integration'),
        ('AI .NET','Beginner / Coursera'),
        ('Building','GHAR / household management'),
    ]
    for i,(key,value) in enumerate(rows):
        row_style=f' class="row" style="animation-delay:{.2+i*.13:.2f}s"' if not static else ''
        parts.append(f'<g{row_style}>')
        parts += [text(24,153+i*25,key,12.5,GREEN),text(108,153+i*25,value,12.5,TEXT),'</g>']
    parts += [f'<line x1="24" y1="350" x2="466" y2="350" stroke="{LINE}"/>',
        text(24,374,'Backend development / continuous learning',11,MUTED)]
    save_svg('info-card.svg',parts)


def render_avatar(path, static=False):
    from PIL import Image, ImageOps
    image = ImageOps.autocontrast(Image.open(path).convert('L')).resize((64,34))
    ramp = ' .:-=+*#%@'
    rows = [''.join(ramp[round((255-image.getpixel((x,y)))/255*(len(ramp)-1))] for x in range(64)) for y in range(34)]
    parts = svg_start(370,390,'Ashish John ASCII GitHub avatar',
        'A monochrome ASCII rendering of my existing GitHub identicon, revealed once line by line.')
    parts += [text(22,35,'ashish@github:~$ avatar',14,BLUE),
        f'<line x1="22" y1="51" x2="348" y2="51" stroke="{LINE}"/>']
    if not static:
        parts.append('<style>@media(prefers-reduced-motion:reduce){.ascii-line{clip-path:none!important}}</style>')
    for i,row in enumerate(rows):
        y = 72+i*8.3
        if not static:
            delay=i*.035
            duration=delay+.25
            timeline=f'values="0;0;328" keyTimes="0;{delay/duration:.4f};1"' if delay else 'values="0;328"'
            parts.append(f'<clipPath id="row-{i}"><rect x="22" y="{y-8}" width="328" height="10"><animate attributeName="width" {timeline} dur="{duration:.3f}s" begin="0s" fill="freeze"/></rect></clipPath>')
        clip=f' class="ascii-line" clip-path="url(#row-{i})"' if not static else ''
        parts.append(text(22,round(y,2),row,8.5,TEXT,'xml:space="preserve"'+clip))
    parts += [f'<line x1="22" y1="350" x2="348" y2="350" stroke="{LINE}"/>',
        text(22,374,'@ashu-ashishjohn',11,MUTED)]
    save_svg('ashish-ascii.svg',parts)


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('--offline', action='store_true', help='Render the saved contribution snapshot')
    argp.add_argument('--avatar', type=Path, help='Regenerate ASCII avatar; requires Pillow locally')
    argp.add_argument('--info', action='store_true', help='Regenerate the info card after editing its content')
    argp.add_argument('--static', action='store_true', help='Render a fully visible frame for previews')
    args = argp.parse_args()
    data_path = ROOT/'contributions.json'
    if args.offline:
        data = json.loads(data_path.read_text(encoding='utf-8'))
    else:
        data = fetch_calendar()
        # Only replace the saved snapshot after a complete, validated response.
        temporary = data_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        temporary.replace(data_path)
    render_heatmap(data,args.static)
    if args.info:
        render_info(args.static)
    if args.avatar:
        render_avatar(args.avatar,args.static)
    print(f"Rendered {len(data['days'])} days for {USERNAME}; total={sum(d['count'] for d in data['days'])}")


if __name__ == '__main__':
    main()
