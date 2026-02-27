import json
import unittest

import webui


class WebUiTestCase(unittest.TestCase):
    def setUp(self):
        webui.JOBS.clear()

    def test_render_index_contains_form(self):
        page = webui.render_index()
        self.assertIn('AppAgent 可视化控制台', page)
        self.assertIn("<form", page)

    def test_render_job_contains_status_endpoint(self):
        job = webui.Job(id='abc123', mode='run', app_name='Demo', root_dir='./')
        html = webui.render_job(job)
        self.assertIn('/jobs/abc123/status', html)

    def test_status_payload_shape(self):
        job = webui.Job(id='j1', mode='run', app_name='Demo', root_dir='./', status='queued')
        webui.JOBS[job.id] = job
        payload = {
            'id': job.id,
            'mode': job.mode,
            'status': job.status,
            'logs': job.logs,
            'started_at': job.started_at,
            'finished_at': job.finished_at,
        }
        self.assertEqual(json.loads(json.dumps(payload))['id'], 'j1')


if __name__ == '__main__':
    unittest.main()
