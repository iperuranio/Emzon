from emzon.settings import dialog_start


def test_the_last_folder_comes_first(tmp_path):
    last, videos = tmp_path / "PUBG", tmp_path / "Videos"
    last.mkdir()
    videos.mkdir()
    assert dialog_start(last, videos) == last


def test_without_a_last_folder_the_videos_folder(tmp_path):
    videos = tmp_path / "Videos"
    videos.mkdir()
    assert dialog_start(None, videos) == videos


def test_a_last_folder_that_is_gone_falls_back_to_videos(tmp_path):
    videos = tmp_path / "Videos"
    videos.mkdir()
    assert dialog_start(tmp_path / "deleted", videos) == videos
