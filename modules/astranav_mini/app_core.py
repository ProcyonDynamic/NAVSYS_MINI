def navsys_mini_boot(
    *,
    usb_root: str,
    strict: bool = False
) -> dict:
    """
    Validates USB structure, creates missing folders, returns capabilities and paths.

    Returns:
    {
      "ok": bool,
      "usb_root": str,
      "paths": { ... },
      "errors": [str]
    }
    """
    raise NotImplementedError