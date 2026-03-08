from .models import WarningDraft, ShipPosition
from .register_ns01 import NS01Row

def run_navwarn_pipeline(
    *,
    draft: WarningDraft,
    ship_position: ShipPosition | None,
    run_id: str,
    processed_utc: str,
    out_processed_dir: str,
    out_plots_dir: str,
    out_reports_dir: str
) -> dict:
    """
    Executes NavWarn A2..A8 and returns a dict:

    {
      "ok": bool,
      "warning_id": str,
      "band": "RED"|"AMBER",
      "distance_nm": float|None,
      "plot_csv_path": str|None,
      "ns01_csv_path": str,
      "ns01_txt_path": str,
      "errors": [str]
    }

    NOTE: Keep it deterministic and silence-by-default.
    """
    raise NotImplementedError