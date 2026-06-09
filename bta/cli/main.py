import typer

app = typer.Typer(
    help="GitHub Bug Triage Agent"
)

@app.command()
def hello():
    print("bug-triage-agent is ready")

if __name__ == "__main__":
    app()