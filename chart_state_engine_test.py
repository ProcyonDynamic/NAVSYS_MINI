from modules.navwarn_mini.chart_state_engine import rebuild_active_chart_session


def test_rebuild_active_chart_session(tmp_path):
    active_csv = tmp_path / "active_warning_table.csv"
    active_csv.write_text(
        "warning_id,navarea,state,source_warning_id,cancel_targets,last_updated_utc,plotted,plot_ref\n"
        "NAVAREA IV 144/26,IV,ACTIVE,NAVAREA IV 144/26,,2026-03-11T23:37:48Z,YES,plot1.csv\n"
        "NAVAREA IV 145/26,IV,CANCELLED,NAVAREA IV 145/26,NAVAREA IV 144/26,2026-03-11T23:37:48Z,NO,\n",
        encoding="utf-8",
    )

    out_csv = tmp_path / "active_chart_manifest.csv"
    result = rebuild_active_chart_session(
        active_table_csv=str(active_csv),
        output_csv_path=str(out_csv),
    )

    assert result["ok"] is True
    assert result["active_count"] == 1
    assert out_csv.exists()