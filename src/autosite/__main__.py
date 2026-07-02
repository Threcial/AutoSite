import sys
import os

pkg_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(pkg_dir)
project_root = os.path.dirname(src_dir)

sys.path.insert(0, src_dir)
os.chdir(project_root)

from autosite.main import main
sys.exit(main())
