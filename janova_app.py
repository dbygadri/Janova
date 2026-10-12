from core.orchestrator import JanovaOrchestrator
from ui.desktop import JanovaDesktopApp


def main() -> None:
    orchestrator = JanovaOrchestrator()
    app = JanovaDesktopApp(orchestrator=orchestrator)
    app.run()


if __name__ == "__main__":
    main()
