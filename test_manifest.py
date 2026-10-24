"""Real local Git fixtures for Service-selected tags and a single stable checkout."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from manifest import synchronize,requirements,registry


class Manifest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='git-tags-');self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.src=self.base/'source';self.src.mkdir()
        self.git(self.src,'init','-q');self.git(self.src,'symbolic-ref','HEAD','refs/heads/main');self.git(self.src,'config','user.name','Fixture');self.git(self.src,'config','user.email','fixture@example.invalid')
        (self.src/'code').write_text('one');self.git(self.src,'add','code');self.git(self.src,'commit','-qm','one');self.git(self.src,'tag','v1')
        (self.src/'code').write_text('two');self.git(self.src,'commit','-qam','two');self.git(self.src,'tag','v2')
        self.origin=self.base/'origin.git';subprocess.run(['git','clone','--bare',str(self.src),str(self.origin)],check=True,capture_output=True)
        self.checkout=self.base/'fixed';self.config=self.base/'config';self.config.mkdir();self.services=self.config/'services';self.services.mkdir()
        self.manifest=self.config/'repos.json';self.manifest.write_text(json.dumps({'code':{'url':str(self.origin),'path':str(self.checkout),'branch':'main'}}))
        self.declare('one','v1');self.logs=[]
    def git(self,path,*args):return subprocess.check_output(['git','-C',str(path),*args],stderr=subprocess.STDOUT,text=True).strip()
    def declare(self,id,tag,node='a'):
        p=self.services/id/'declaration.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(dict(kind='Service',id=id,node=node,repos={'code':tag})))
    def sync(self):return synchronize(self.manifest,self.services,'a',self.logs.append)
    def test_clone_switch_tag_same_directory_and_reload_declarations(self):
        self.assertTrue(self.sync(),self.logs);self.assertEqual((self.checkout/'code').read_text(),'one')
        self.declare('one','v2');self.assertTrue(self.sync(),self.logs)
        self.assertEqual((self.checkout/'code').read_text(),'two');self.assertEqual(list(self.base.glob('fixed*')),[self.checkout])
    def test_conflict_does_not_switch_either_service(self):
        self.assertTrue(self.sync());before=self.git(self.checkout,'rev-parse','HEAD')
        self.declare('two','v2');self.assertFalse(self.sync())
        self.assertEqual(self.git(self.checkout,'rev-parse','HEAD'),before)
        self.assertIn('conflicting Service tags',self.logs[-1])
    def test_dirty_and_unpublished_work_are_preserved(self):
        self.assertTrue(self.sync());self.declare('one','v2');(self.checkout/'code').write_text('local edit')
        self.assertFalse(self.sync());self.assertEqual((self.checkout/'code').read_text(),'local edit')
        self.git(self.checkout,'config','user.name','Fixture');self.git(self.checkout,'config','user.email','fixture@example.invalid')
        self.git(self.checkout,'commit','-qam','unpublished');before=self.git(self.checkout,'rev-parse','HEAD')
        self.assertFalse(self.sync());self.assertEqual(self.git(self.checkout,'rev-parse','HEAD'),before)
    def test_missing_and_moved_tag_refused(self):
        self.assertTrue(self.sync());self.declare('one','absent');self.assertFalse(self.sync())
        self.declare('one','v1');self.git(self.src,'tag','-f','v1','v2');self.git(self.src,'push','--force',str(self.origin),'refs/tags/v1')
        self.assertFalse(self.sync());self.assertEqual((self.checkout/'code').read_text(),'one')
    def test_other_node_requirements_do_not_conflict(self):
        self.declare('two','v2','b');self.assertTrue(self.sync(),self.logs)
    def test_untracked_files_survive_tag_switch(self):
        self.assertTrue(self.sync());(self.checkout/'notes').write_text('keep')
        self.declare('one','v2');self.assertTrue(self.sync(),self.logs);self.assertEqual((self.checkout/'notes').read_text(),'keep')

if __name__=='__main__':unittest.main()
