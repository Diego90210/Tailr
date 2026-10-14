import sys
from pathlib import Path

# services/docgen is not a package; make `import cvdoc` work from tests/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
