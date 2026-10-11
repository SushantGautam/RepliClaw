"""Fast safety tests for Copilot CLI fleet hook/heartbeat helper (stdlib only)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'copilot_fleet_watch.py'


class FleetWatchTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.env = {**os.environ, 'REPLICLAW_FLEET_DIR': self.root.name}

    def call(self, *args, input=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=input, text=True,
                              capture_output=True, env=self.env)

    def test_assignment_heartbeat_and_completion(self):
        self.assertEqual(self.call('assign','FF-01','--agent','rc-fast','--progress','fix CI').returncode, 0)
        beat = self.call('beat', 'FF-01', '--progress', 'dependency patch', '--artifact', 'pyproject.toml')
        self.assertEqual(beat.returncode, 0)
        result = self.call('watch', '--json')
        self.assertEqual(json.loads(result.stdout)['tasks'][0]['health'], 'ACTIVE')
        done = self.call('done', 'FF-01', '--progress', 'passed')
        self.assertEqual(done.returncode, 0)
        self.assertEqual(json.loads(self.call('watch','--json').stdout)['tasks'][0]['health'],'DONE')
        self.assertNotEqual(self.call('beat','FF-01','--progress','late').returncode,0)

    def test_missing_progress_detected_even_with_beat(self):
        self.call('assign','FF-02','--agent','rc-implement')
        p=Path(self.root.name)/'tasks'/'FF-02.json'
        data = json.loads(p.read_text())
        data['last_progress'] -= 900
        p.write_text(json.dumps(data))
        r = self.call('watch', '--json')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)['tasks'][0]['health'],'NO_MEASURABLE_PROGRESS')

    def test_stale_heartbeat_detected(self):
        self.call('assign','FF-02','--agent','rc-implement')
        p=Path(self.root.name)/'tasks'/'FF-02.json'
        data = json.loads(p.read_text())
        data['last_beat'] -= 900
        p.write_text(json.dumps(data))
        r = self.call('watch', '--json')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)['tasks'][0]['health'],'STALE_HEARTBEAT')

    def test_reject_invalid_task_id(self):
        self.assertEqual(self.call('assign','../../oops','--agent','rc-fast').returncode,2)
        self.assertFalse(list(Path(self.root.name).glob('tasks/*')))

    def test_hook_redacts_payloads(self):
        payload={'sessionId':'secret-session','agentName':'rc-implement',
                 'response':'password=SECRETKEY','toolResult':{'textResultForLlm':'TOKEN-SECRET'}}
        s=self.call('hook','subagentStart',input=json.dumps(payload))
        self.assertEqual(s.returncode,0)
        self.assertIn('additionalContext',json.loads(s.stdout))
        self.assertNotIn('secret-session',str(list(Path(self.root.name).rglob('*.json'))))
        for f in Path(self.root.name).rglob('*.json'):
            self.assertNotIn('SECRET',f.read_text())

    def test_one_stop_retry_then_accept(self):
        payload={'sessionId':'a', 'agentId':'agent1','agentName':'rc-fast','response':'bad result'}
        a=self.call('hook','subagentStop',input=json.dumps(payload))
        self.assertEqual(json.loads(a.stdout)['decision'],'block')
        b=self.call('hook','subagentStop',input=json.dumps(payload))
        self.assertEqual(json.loads(b.stdout),{})
        payload['response']='STATUS: DONE\nARTIFACT: f\nCHECK: ok'
        c=self.call('hook','subagentStop',input=json.dumps(payload))
        self.assertEqual(json.loads(c.stdout),{})


if __name__=='__main__':
    unittest.main()
