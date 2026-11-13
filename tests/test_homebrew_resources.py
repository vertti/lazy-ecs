from generate_homebrew_resources import render_resources

LOCK = {
    "package": [
        {"name": "lazy-ecs", "version": "0.9.0", "source": {"editable": "."}},
        {
            "name": "rich",
            "version": "15.0.0",
            "sdist": {"url": "https://files.example/rich-15.0.0.tar.gz", "hash": "sha256:aaa"},
        },
        {
            "name": "six",
            "version": "1.17.0",
            "sdist": {"url": "https://files.example/six-1.17.0.tar.gz", "hash": "sha256:bbb"},
        },
        {
            "name": "moto",
            "version": "5.2.3",
            "sdist": {"url": "https://files.example/moto-5.2.3.tar.gz", "hash": "sha256:ccc"},
        },
    ]
}


def test_renders_only_exported_packages_from_lock():
    export = "rich==15.0.0\nsix==1.17.0 ; python_version >= '3.11'\n"

    assert render_resources(export, LOCK) == (
        '  resource "rich" do\n'
        '    url "https://files.example/rich-15.0.0.tar.gz"\n'
        '    sha256 "aaa"\n'
        "  end\n"
        "\n"
        '  resource "six" do\n'
        '    url "https://files.example/six-1.17.0.tar.gz"\n'
        '    sha256 "bbb"\n'
        "  end"
    )
