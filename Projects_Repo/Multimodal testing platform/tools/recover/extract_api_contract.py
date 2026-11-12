"""Extract the authoritative HTTP contract (routes, signatures, models) from app.main bytecode.

The original module-level bytecode is executed against stub fastapi/pydantic modules, so
every route decorator, function signature, default value and pydantic field is produced by
the original code itself rather than guessed from decompiler output.
"""
import importlib.util
import inspect
import json
import marshal
import os
import sys
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(PROJECT, "_recovered_raw")
PYC = os.path.join(PROJECT, "_src", "_pyc")


class Sentinel:
    def __init__(self, kind, args, kwargs):
        self.kind, self.args, self.kwargs = kind, args, kwargs

    def __repr__(self):
        parts = [repr(a) for a in self.args]
        parts += [f"{k}={v!r}" for k, v in self.kwargs.items()]
        return f"{self.kind}({', '.join(parts)})"


def sentinel(kind):
    def factory(*args, **kwargs):
        return Sentinel(kind, args, kwargs)
    return factory


class RouteRecorder:
    def __init__(self, *args, **kwargs):
        self.title = kwargs.get("title")
        self.routes = []
        self.events = []

    def _register(self, method):
        def decorator(path, **kwargs):
            def wrap(fn):
                self.routes.append({"method": method, "path": path, "fn": fn.__name__,
                                    "kwargs": kwargs, "callable": fn})
                return fn
            return wrap
        return decorator

    def get(self, path, **kw): return self._register("GET")(path, **kw)
    def post(self, path, **kw): return self._register("POST")(path, **kw)
    def put(self, path, **kw): return self._register("PUT")(path, **kw)
    def delete(self, path, **kw): return self._register("DELETE")(path, **kw)

    def mount(self, path, sub, **kw):
        self.events.append({"kind": "mount", "path": path, "sub": repr(sub), **kw})

    def add_middleware(self, cls, **kw):
        self.events.append({"kind": "middleware", "cls": getattr(cls, "__name__", repr(cls)), **kw})

    def add_exception_handler(self, cls, handler):
        self.events.append({"kind": "exception_handler", "exc": getattr(cls, "__name__", repr(cls)),
                            "handler": getattr(handler, "__name__", repr(handler))})

    def exception_handler(self, cls):
        def wrap(fn):
            self.events.append({"kind": "exception_handler", "exc": getattr(cls, "__name__", repr(cls)),
                                "handler": fn.__name__})
            return fn
        return wrap

    def on_event(self, name):
        def wrap(fn):
            self.events.append({"kind": "event", "event": name, "handler": fn.__name__})
            return fn
        return wrap


class ModelRecorder:
    registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        ModelRecorder.registry[cls.__name__] = cls

    def dict(self):
        return dict(self.__dict__)


def build_stubs():
    fastapi = types.ModuleType("fastapi")
    fastapi.FastAPI = RouteRecorder
    fastapi.HTTPException = type("HTTPException", (Exception,), {
        "__init__": lambda self, status_code=500, detail="": (
            setattr(self, "status_code", status_code), setattr(self, "detail", detail), None)[2]})
    fastapi.UploadFile = type("UploadFile", (), {"__repr__": lambda self: "UploadFile"})
    fastapi.File = sentinel("File")
    fastapi.Form = sentinel("Form")
    fastapi.Query = sentinel("Query")
    fastapi.Body = sentinel("Body")
    fastapi.Path = sentinel("Path")

    responses = types.ModuleType("fastapi.responses")
    responses.FileResponse = type("FileResponse", (), {"__init__": lambda self, *a, **k: None})
    responses.JSONResponse = type("JSONResponse", (), {"__init__": lambda self, *a, **k: None})

    staticfiles = types.ModuleType("fastapi.staticfiles")
    staticfiles.StaticFiles = type("StaticFiles", (), {"__init__": lambda self, *a, **k: None,
                                                       "__repr__": lambda self: "StaticFiles(web)"})

    pydantic = types.ModuleType("pydantic")
    pydantic.BaseModel = ModelRecorder
    pydantic.Field = sentinel("Field")

    sys.modules.update({"fastapi": fastapi, "fastapi.responses": responses,
                        "fastapi.staticfiles": staticfiles, "pydantic": pydantic})


def load_sibling(name):
    path = os.path.join(RAW, "app." + name + ".py")
    spec = importlib.util.spec_from_file_location("app." + name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["app." + name] = module
    spec.loader.exec_module(module)
    return module


def describe_callable(fn):
    sig = inspect.signature(fn)
    params = []
    for p in sig.parameters.values():
        params.append({
            "name": p.name,
            "kind": str(p.kind),
            "annotation": None if p.annotation is inspect._empty else repr(p.annotation),
            "default": None if p.default is inspect._empty else repr(p.default),
            "has_default": p.default is not inspect._empty,
        })
    return params


def main():
    build_stubs()
    package = types.ModuleType("app")
    package.__path__ = [RAW]
    sys.modules["app"] = package

    for name in ["config", "dircache", "annotate", "comparison", "schema", "prompts",
                 "prompt_profiles", "datasets", "truth", "maas", "runner", "evaluate",
                 "extractor", "reviews", "judge", "prompt_ai", "workflow", "stats",
                 "trial", "demo"]:
        try:
            module = load_sibling(name)
            setattr(package, name, module)
            sys.modules["app." + name] = module
        except Exception as exc:  # missing module is recorded, not fatal
            stub = types.ModuleType("app." + name)
            stub.__getattr__ = lambda attr: (lambda *a, **k: None)
            sys.modules["app." + name] = stub
            setattr(package, name, stub)
            print(f"[warn] app.{name} not loadable: {type(exc).__name__}: {exc}", file=sys.stderr)

    with open(os.path.join(PYC, "app.main.pyc"), "rb") as fh:
        code = marshal.loads(fh.read()[16:])

    namespace = {"__name__": "app.main", "__package__": "app",
                 "__file__": os.path.join(RAW, "app.main.py")}
    exec(code, namespace)

    app = namespace["app"]
    out = {"title": app.title, "events": app.events, "routes": [], "models": {}}

    for route in app.routes:
        out["routes"].append({
            "method": route["method"],
            "path": route["path"],
            "fn": route["fn"],
            "kwargs": {k: repr(v) for k, v in route["kwargs"].items()},
            "params": describe_callable(route["callable"]),
            "doc": inspect.getdoc(route["callable"]),
        })

    for name, cls in ModelRecorder.registry.items():
        annotations = cls.__dict__.get("__annotations__", {})
        defaults = {}
        for key, value in cls.__dict__.items():
            if key in annotations or key.startswith("__"):
                continue
            if isinstance(value, (str, int, float, bool, type(None), Sentinel, list, dict)):
                defaults[key] = repr(value)
        out["models"][name] = {
            "bases": [b.__name__ for b in cls.__bases__],
            "annotations": {k: repr(v) for k, v in annotations.items()},
            "defaults": defaults,
        }

    dest = os.path.join(PROJECT, "_analysis", "api_contract.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"routes={len(out['routes'])} models={len(out['models'])} events={len(out['events'])} -> {dest}")


if __name__ == "__main__":
    main()
