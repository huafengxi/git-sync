"""One fixed Git checkout per repository, selected by local Service tags."""
import json
import os
from pathlib import Path
import subprocess


def require(ok,message):
    if not ok:raise ValueError(message)


def git(path,*args):
    r=subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True,timeout=120)
    require(r.returncode==0,' '.join(args[:2])+': '+(r.stderr or r.stdout).strip())
    return r.stdout.strip()


def registry(path,node):
    data=json.loads(Path(path).read_text());require(isinstance(data,dict),'repository map required')
    result={};paths=set()
    for key,spec in data.items():
        require(isinstance(spec,dict) and set(spec)<= {'url','path','branch','nodes'} and {'url','path','branch'}<=set(spec),'invalid repository: '+key)
        require(all(isinstance(spec[k],str) and spec[k] for k in ('url','path','branch')),'nonempty repository fields required')
        if spec.get('nodes') and node not in spec['nodes']:continue
        target=Path(spec['path']).expanduser();require(target.is_absolute(),'absolute checkout path required')
        real=target.resolve();require(real not in paths,'duplicate checkout path: '+str(target));paths.add(real)
        result[key]=dict(spec,path=str(target))
    return result


def requirements(services,node,repos):
    result={}
    for p in Path(services).rglob('declaration.json'):
        d=json.loads(p.read_text())
        if d.get('kind')!='Service' or d['node']!=node:continue
        refs=d.get('repos',{});require(isinstance(refs,dict),'Service repos must be a map')
        for key,tag in refs.items():
            require(key in repos,'unregistered repository: '+key)
            require(isinstance(tag,str) and tag and not tag.startswith('-'),'invalid tag')
            check=subprocess.run(['git','check-ref-format','refs/tags/'+tag],capture_output=True)
            require(check.returncode==0,'invalid tag: '+tag)
            require(key not in result or result[key]==tag,'conflicting Service tags: '+key)
            result[key]=tag
    return result


def sync_one(spec,tag=None):
    path=Path(spec['path'])
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        r=subprocess.run(['git','clone','--origin','origin','--branch',spec['branch'],'--',spec['url'],str(path)],capture_output=True,text=True,timeout=120)
        require(r.returncode==0,'clone failed: '+r.stderr.strip())
    require((path/'.git').exists(),'checkout required: '+str(path))
    require(git(path,'remote','get-url','origin')==spec['url'],'origin differs from manifest: '+str(path))
    require(not git(path,'status','--porcelain','-uno'),'tracked edits in '+str(path))
    # Older Git can overwrite tags even without --force. Fetch branches only,
    # compare published tag identities, then create the requested tag atomically.
    remote={line.split()[1]:line.split()[0] for line in git(path,'ls-remote','--tags','origin').splitlines() if not line.endswith('^{}')}
    local={line.split()[0]:line.split()[1] for line in git(path,'for-each-ref','--format=%(refname) %(objectname)','refs/tags').splitlines()}
    require(all(local[ref]==remote[ref] for ref in local.keys() & remote.keys()),'published tag moved')
    git(path,'fetch','--no-tags','origin','refs/heads/*:refs/remotes/origin/*')
    if tag:
        ref='refs/tags/'+tag
        require(ref in remote,'missing published tag: '+tag)
        if ref not in local:
            git(path,'fetch','--no-tags','origin',ref)
            require(git(path,'rev-parse','FETCH_HEAD')==remote[ref],'tag changed during fetch')
            git(path,'update-ref',ref,remote[ref],'0'*len(remote[ref]))
    require(git(path,'rev-list','--count','HEAD','--not','--remotes=origin')=='0','unpublished commits in '+str(path))
    if tag:
        target=git(path,'rev-parse','--verify','refs/tags/'+tag+'^{commit}')
        if git(path,'rev-parse','HEAD')!=target:
            git(path,'checkout','--no-overwrite-ignore','--detach','refs/tags/'+tag)
    else:
        branch=git(path,'symbolic-ref','--quiet','--short','HEAD')
        require(branch==spec['branch'],'branch differs from manifest: '+str(path))
        git(path,'merge','--ff-only','refs/remotes/origin/'+spec['branch'])


def synchronize(manifest,services,node,log=print):
    """Reload control checkout first, then validate all pins before any tag switch."""
    try:
        repos=registry(manifest,node)
        control=Path(manifest).resolve().parent
        for key,spec in repos.items():
            if Path(spec['path']).resolve()==control:
                sync_one(spec)
        repos=registry(manifest,node);pins=requirements(services,node,repos)
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as e:
        log('manifest ERROR: '+str(e));return False
    ok=True
    for key,spec in repos.items():
        try:sync_one(spec,pins.get(key))
        except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as e:
            log('['+key+'] SKIP: '+str(e));ok=False
    return ok
