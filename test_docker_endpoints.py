import docker_focused_app


def test_list_containers_includes_first_formatted_row(monkeypatch):
    """Docker --format output has no header, so the first row is a container."""
    sample_output = (
        "abc123456789\tweb\tUp 2 hours\t0.0.0.0:80->80/tcp\n"
        "def987654321\tdb\tExited (0) 1 hour ago\t5432/tcp\n"
    )

    monkeypatch.setattr(
        docker_focused_app,
        "execute_ssh_command_via_paramiko",
        lambda host, user, password, command: (sample_output, ""),
    )

    with docker_focused_app.app.test_client() as client:
        response = client.get("/containers")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": "abc123456789",
            "name": "web",
            "status": "Up 2 hours",
            "ports": "0.0.0.0:80->80/tcp",
        },
        {
            "id": "def987654321",
            "name": "db",
            "status": "Exited (0) 1 hour ago",
            "ports": "5432/tcp",
        },
    ]


def test_list_images_includes_first_formatted_row(monkeypatch):
    """Docker images --format output has no header, so the first row is an image."""
    sample_output = (
        "sha256:111111111111\tnginx\tlatest\t190MB\n"
        "sha256:222222222222\tpostgres\t16\t430MB\n"
    )

    monkeypatch.setattr(
        docker_focused_app,
        "execute_ssh_command_via_paramiko",
        lambda host, user, password, command: (sample_output, ""),
    )

    with docker_focused_app.app.test_client() as client:
        response = client.get("/images")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": "sha256:11111",
            "repository": "nginx",
            "tag": "latest",
            "size": "190MB",
        },
        {
            "id": "sha256:22222",
            "repository": "postgres",
            "tag": "16",
            "size": "430MB",
        },
    ]
