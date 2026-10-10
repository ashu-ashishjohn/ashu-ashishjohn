"""Refresh public-only profile data and cache keys; standard library only."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib, json, re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
USERNAME='ashu-ashishjohn'
SVG='http://www.w3.org/2000/svg'
ET.register_namespace('',SVG)

def get_json(url):
    # Deliberately unauthenticated: private repositories cannot enter the output.
    req=Request(url,headers={'User-Agent':USERNAME+'-public-profile','Accept':'application/vnd.github+json'})
    with urlopen(req,timeout=30) as response:return json.loads(response.read())

def update_svg(name,updates,widths=None):
    path=ROOT/name
    tree=ET.parse(path)
    elements={e.get('id'):e for e in tree.iter() if e.get('id')}
    for key,value in updates.items():
        if key not in elements:raise ValueError('Missing dashboard element: '+key)
        elements[key].text=str(value)
    for key,value in (widths or {}).items():elements[key].set('width',str(value))
    tree.write(path,encoding='unicode',xml_declaration=False)
    with path.open('a',encoding='utf-8') as output:output.write('\n')

def main():
    user=get_json('https://api.github.com/users/'+USERNAME)
    repos=[]
    for page in range(1,21):
        current=get_json(f'https://api.github.com/users/{USERNAME}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(current,list):raise ValueError('Unexpected public repository response')
        repos.extend(r for r in current if not r['private'])
        if len(current)<100:break
    else:raise ValueError('Public repository list exceeded supported pagination')
    if len(repos)!=user['public_repos']:raise ValueError('Incomplete public repository response')
    stars=sum(r['stargazers_count'] for r in repos)
    now=datetime.now(timezone.utc)
    data={'username':USERNAME,'public_repos':len(repos),'followers':user['followers'],'stars':stars,'updated_at':now.isoformat(timespec='seconds'),'repos':[{'name':r['name'],'stars':r['stargazers_count'],'language':r['language'],'url':r['html_url']} for r in repos]}
    (ROOT/'public-stats.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    update_svg('hero.svg',{'hero-public-stats':f"India   /   {len(repos)} public repos   /   {stars} stars"})
    updates={'id-dashboard-stat-repos':len(repos),'id-dashboard-stat-stars':stars,'id-dashboard-stat-followers':user['followers'],'dashboard-updated':now.strftime('%d %b %Y')}
    projects=sorted((r for r in repos if r['name']!=USERNAME),key=lambda r:(-r['stargazers_count'],r['name']))[:2]
    maximum=max([r['stargazers_count'] for r in projects]+[1])
    widths={}
    for i in range(2):
        r=projects[i] if i<len(projects) else None
        name=r['name'] if r else 'No public project'
        label=name if len(name)<=25 else name[:22]+'...'
        value=r['stargazers_count'] if r else 0
        updates[f'id-dashboard-repo-name-{i}']=label
        updates[f'id-dashboard-repo-stars-{i}']=value
        widths[f'id-dashboard-repo-bar-{i}']=round(262*value/maximum,2)
    update_svg('id-dashboard.svg',updates,widths)
    readme=ROOT/'README.md'
    if readme.exists():
        content=readme.read_text(encoding='utf-8')
        for path in [*ROOT.glob('*.svg'),ROOT/'profile-3d-contrib'/'profile-night-view.svg']:
            if path.exists():
                rel=path.relative_to(ROOT).as_posix()
                digest=hashlib.sha256(path.read_bytes()).hexdigest()[:12]
                content=re.sub(r'(\./'+re.escape(rel)+r')(?:\?v=[a-zA-Z0-9_-]+)?',lambda m:m[1]+'?v='+digest,content)
        readme.write_text(content,encoding='utf-8')
    print(f'Updated public-only metrics: {len(repos)} repositories, {stars} stars, {user["followers"]} followers.')

if __name__=='__main__':main()
