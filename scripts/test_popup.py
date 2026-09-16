from unittest.mock import patch
import quota_watcher as w
with patch.object(w.subprocess, 'Popen') as start, patch.object(w, 'save_state') as save:
    state = {}
    w.offer_plan({'threadId': '00000000-0000-0000-0000-000000000001', 'key': 'new'}, state)
    start.assert_not_called()
    save.assert_not_called()
    assert state == {}
print('NO_AUTO_POPUP_OK')
