from dataclasses import asdict, dataclass, field
from pathlib import Path

from scidock.log import logger
from scidock.meta import SearchResult
from scidock.utils import dump_json, emergency_exit, global_config_exists, load_json

__all__ = ('global_config', 'repo_config')


def default_repo_config() -> str:
    default_repo = global_config.repositories[global_config.default]
    return str(Path(default_repo) / '.scidock/content.json')


@dataclass
class GlobalConfig:
    path: str

    server_url: str = ''
    repositories: dict[str, str] = field(default_factory=dict)
    default: str = ''
    proxy: str | None = None

    def load(self):
        self.__dict__.update(load_json(self.path))
        self.remove_outdated_repos()

    def dump(self):
        self.remove_outdated_repos()
        dump_json(self, self.path)

    def remove_outdated_repos(self):
        up_to_date_repos = {}

        for name, path in self.repositories.items():
            if Path(path).exists():
                up_to_date_repos[name] = path

        if not up_to_date_repos:
            logger.error(
                "You have no active repos left... Exiting. On the next run you'll be prompted to create one"
            )
            emergency_exit()

        self.repositories = up_to_date_repos
        self.default = list(up_to_date_repos.keys())[-1]


@dataclass
class RepoConfig:
    path: str

    content: list[dict] = field(default_factory=list)
    wishlist: list[dict] = field(default_factory=list)
    search_history: list[str] = field(default_factory=list)

    def load(self):
        self.__dict__.update(load_json(self.path))

    def dump(self):
        dump_json(self, self.path)

    def migrate(self):
        self.path = default_repo_config()

        if Path(self.path).expanduser().exists():
            self.load()
        else:
            # reset current instance to defaults
            default_config = RepoConfig(self.path)
            self.__dict__ = default_config.__dict__

            self.dump()

    def add_to_wishlist(self, result: SearchResult):
        result = asdict(result)
        if result not in self.wishlist:
            self.wishlist.append(result)
            self.dump()

    def add_to_content(self, result: SearchResult):
        result = asdict(result)
        if result not in self.content:
            self.content.append(result)
            self.dump()

    def add_to_search_history(self, query: str):
        if query in self.search_history:
            self.search_history.remove(query)

        self.search_history.append(query)
        self.dump()

    @property
    def repo_path(self):
        return Path(self.path).expanduser().parent.parent


global_config = GlobalConfig('~/.scidock/config.json')
repo_config = RepoConfig('')

if global_config_exists():
    global_config.load()
    repo_config.migrate()
