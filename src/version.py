import git

def GetVersion():
    r = git.repo.Repo(search_parent_directories=True)
    return r.git.describe("--tags")
__VERSION__ = GetVersion()
