"""Create a synthetic 'download folder' for manual runs: python tests/make_synthetic.py DIR"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_photocull import make_download  # noqa: E402

make_download(Path(sys.argv[1]))
