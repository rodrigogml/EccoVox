from scripts.manager_menu import MenuApplication


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def configure_assignments(self, assignments):
        self.calls.append(("configure", *assignments))
        return {"ok": True}

    def configuration_values(self):
        return {"tts.warmup": True}

    def install(self, extras):
        self.calls.append(("install", extras))

    def __getattr__(self, name):
        def operation(*args, **kwargs):
            self.calls.append((name, *args, *kwargs.values()))

        return operation


def test_main_menu_routes_to_nested_server_configuration() -> None:
    backend = FakeBackend()
    answers = iter(("4", "5", "9123", "0", "0"))
    output: list[str] = []
    app = MenuApplication(backend, read=lambda _prompt: next(answers), write=output.append)

    assert app.run() == 0
    assert ("configure", "server.port=9123") in backend.calls
    assert any("Servidor e rede" in line for line in output)


def test_destructive_service_removal_requires_strong_confirmation() -> None:
    backend = FakeBackend()
    answers = iter(("3", "6", "não", "0", "0"))
    app = MenuApplication(backend, read=lambda _prompt: next(answers), write=lambda _text: None)

    app.run()

    assert not any(call[0] == "service_remove" for call in backend.calls)


def test_gpu_installation_preset_is_closed_and_explicit() -> None:
    backend = FakeBackend()
    answers = iter(("1", "1", "0", "0"))
    app = MenuApplication(backend, read=lambda _prompt: next(answers), write=lambda _text: None)

    app.run()

    assert ("install", "stt-gpu,tts,service") in backend.calls
