import os
import git

r = git.repo.Repo()
os.rename(os.path.join('dist','HondaECU.exe'),os.path.join('dist','HondaECU_%s.exe' % (r.git.describe("--tags"))))
