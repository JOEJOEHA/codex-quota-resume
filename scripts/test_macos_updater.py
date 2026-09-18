"""Offline Mac release checks never install or trust an external release URL."""
import io
import json
import unittest
from unittest.mock import patch
import updater as u


class UpdateTests(unittest.TestCase):
    def release(self,tag='v3.0.0-beta.37',machine='arm64'):
        asset=f'CodexQuotaResume-macOS-{machine}-preview.zip'
        return {'tag_name':tag,'draft':False,'body':'Release notes','html_url':'https://untrusted.example',
                'assets':[{'name':asset,'browser_download_url':f'https://github.com/{u.REPO}/releases/download/{tag}/{asset}'}]}

    def check(self,releases,**kwargs):
        with patch.object(u,'fetch',return_value=io.BytesIO(json.dumps(releases).encode())) as fetch,patch.object(u.subprocess,'run') as run,patch.object(u.subprocess,'Popen') as launch:
            result=u.check_macos_update(current='3.0.0-beta.36',machine='arm64',**kwargs)
            self.assertEqual(fetch.call_count,1)
            run.assert_not_called();launch.assert_not_called()
            return result

    def test_beta_version(self):
        self.assertEqual(u.version('v3.1.0beta'), u.version('3.1.0-beta.0'))
        self.assertEqual(u.version('v3.1.0bata'), u.version('3.1.0-beta.0'))
        self.assertGreater(u.version('3.1.0bata'), u.version('3.0.0-beta.38'))
        self.assertLess(u.version('3.1.0bata'), u.version('3.1.0'))
        result = self.check([self.release('v3.1.0bata')])
        self.assertEqual(result['version'], 'v3.1.0bata')
        self.assertTrue(result['available'])

    def test_latest_and_architecture(self):
        draft=self.release('v9.0.0');draft['draft']=True
        result=self.check([self.release('v3.0.0-beta.35'),self.release(),draft])
        self.assertTrue(result['available'])
        self.assertEqual(result['notes'],'Release notes')
        self.assertEqual(result['releaseUrl'],f'https://github.com/{u.REPO}/releases/tag/v3.0.0-beta.37')
        self.assertIn('arm64',result['downloadUrl'])

    def test_missing_mac_asset_still_offers_release_page(self):
        self.assertIsNone(self.check([self.release(machine='x86_64')])['downloadUrl'])

    def test_same_version(self):
        self.assertFalse(self.check([self.release('v3.0.0-beta.36')])['available'])

    def test_mismatched_asset_url_rejected(self):
        release=self.release();release['assets'][0]['browser_download_url']='https://untrusted.example/app.zip'
        with self.assertRaises(RuntimeError):self.check([release])

    def test_rate_limit_fallback(self):
        response=io.BytesIO();response.geturl=lambda:f'https://github.com/{u.REPO}/releases/tag/v3.0.0'
        error=u.urllib.error.HTTPError('api',429,'limit',{},None)
        with patch.object(u,'fetch',side_effect=[error,response]):
            result=u.check_macos_update(current='3.0.0-beta.36',machine='arm64')
        self.assertTrue(result['available'] and result['limited'])
        self.assertIsNone(result['downloadUrl'])

    def test_untrusted_fallback_rejected(self):
        for url in ('https://evil.example/v4.0.0',f'https://github.com/{u.REPO}/releases/tag/../../evil'):
            response=io.BytesIO();response.geturl=lambda:url
            with patch.object(u,'fetch',side_effect=[u.urllib.error.HTTPError('api',403,'limit',{},None),response]):
                with self.assertRaises(RuntimeError):u.check_macos_update()

    def test_other_http_errors_propagate(self):
        with patch.object(u,'fetch',side_effect=u.urllib.error.HTTPError('api',500,'error',{},None)):
            with self.assertRaises(u.urllib.error.HTTPError):u.check_macos_update()


if __name__=='__main__':unittest.main()
