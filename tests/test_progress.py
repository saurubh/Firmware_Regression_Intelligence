from fri.utils.progress import ProgressBar


def test_progress_bar_does_not_raise(capsys):
    bar = ProgressBar("edk2", 4)
    bar._tty = False
    bar.update(1, "abcd1234")
    bar.update(4, "ffffeeee")
    bar.close()
    err = capsys.readouterr().err
    assert "FRI edk2" in err
    assert "1/4" in err
