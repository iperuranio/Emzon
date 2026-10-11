from emzon.player.audio_graph import complex_graph, mix_filter, volume_filter


def test_no_audio_needs_no_graph():
    assert complex_graph(0) == ""
    assert mix_filter([]) == ""


def test_single_track_is_converted_to_stereo():
    assert complex_graph(1) == "[aid1]aformat=channel_layouts=stereo[ao]"
    assert mix_filter([0.5]) == "@mix:lavfi=[volume@t1=0.500]"


def test_two_tracks_are_merged_and_split_back_in_stereo_pairs():
    assert complex_graph(2) == (
        "[aid1]aformat=channel_layouts=stereo[s1];"
        "[aid2]aformat=channel_layouts=stereo[s2];"
        "[s1][s2]amerge=inputs=2[ao]"
    )
    assert mix_filter([1.0, 0.6]) == (
        "@mix:lavfi=[asplit=2[i0][i1];"
        "[i0]pan=stereo|c0=c0|c1=c1,volume@t1=1.000[m0];"
        "[i1]pan=stereo|c0=c2|c1=c3,volume@t2=0.600[m1];"
        "[m0][m1]amix=inputs=2:normalize=0]"
    )


def test_volume_filters_are_numbered_from_one():
    assert volume_filter(0) == "volume@t1"
    assert volume_filter(2) == "volume@t3"
