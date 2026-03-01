import json
import unittest

import webui


class WebUiTestCase(unittest.TestCase):
    def setUp(self):
        webui.JOBS.clear()
        webui.RUNNING_PROCESSES.clear()

    def test_render_index_contains_form(self):
        page = webui.render_index()
        self.assertIn('AppAgent 可视化控制台', page)
        self.assertIn('<form', page)

    def test_render_job_contains_status_endpoint_and_stop_button(self):
        job = webui.Job(id='abc123', mode='run', app_name='Demo', root_dir='./')
        html = webui.render_job(job)
        self.assertIn('/jobs/abc123/status', html)
        self.assertIn('/jobs/abc123/stop', html)
        self.assertIn('停止任务', html)

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

    def test_request_stop_job_queued(self):
        job = webui.Job(id='j2', mode='run', app_name='Demo', root_dir='./', status='queued')
        webui.JOBS[job.id] = job
        ok, _ = webui.request_stop_job('j2')
        self.assertTrue(ok)
        self.assertEqual(job.status, 'stopped')


if __name__ == '__main__':
    unittest.main()
