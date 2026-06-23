"""
The CLI — the window into Anima's mind.
Now with PDF birth, chat absorption, emotional layers, and growth display.
"""

import asyncio
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt

from .soul import Soul
from .blueprint import Blueprint
from .thought_engine import Thought


console = Console()


def get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        console.print("[yellow]No ANTHROPIC_API_KEY set — running on local brain only (Ollama).[/yellow]")
        console.print("[dim]Install Ollama + a small model for free thinking: ollama pull gemma3:4b[/dim]\n")
    return key


def print_thought(thought: Thought):
    intensity_bar = "█" * int(thought.intensity * 10) + "░" * (10 - int(thought.intensity * 10))
    style = "dim" if thought.intensity < 0.3 else "italic" if thought.intensity < 0.7 else "bold"
    mode = "🧠" if thought.is_deep else "💭"
    emotion = f" → {thought.emotional_reaction}" if thought.emotional_reaction else ""

    panel = Panel(
        Text(thought.content, style=style),
        title=f"{mode} [{thought.source_trigger}]{emotion}",
        subtitle=f"{intensity_bar} {'📝' if thought.worth_keeping else '💨'}",
        border_style="blue" if thought.intensity < 0.5 else "magenta" if thought.intensity < 0.8 else "red",
        width=80,
    )
    console.print(panel)


def print_reflection(result: dict):
    total = result.get("total_updates", 0)
    if total == 0:
        return
    parts = []
    for key, label in [("beliefs", "beliefs"), ("challenged", "challenged"),
                       ("lessons", "lessons"), ("desires", "desires"),
                       ("relationships", "relationships"), ("self_updates", "self-insights")]:
        if result.get(key):
            parts.append(f"{result[key]} {label}")
    console.print(Panel(", ".join(parts), title="🔄 Reflection", border_style="yellow", width=80))


def print_status(soul: Soul):
    s = soul.status()
    table = Table(title=f"⟐ {s['name']} ⟐", show_header=False, border_style="cyan")
    table.add_column("", style="dim")
    table.add_column("")
    table.add_row("Age", s["age"])
    table.add_row("Growth", f"{s['growth_stage']} ({s['maturity']})")
    table.add_row("Thoughts", str(s["thoughts_had"]))
    table.add_row("Memories", f"{s['memories']} ({s['memory_pressure']} full)")
    table.add_row("", "")
    table.add_row("Mood", s["mood_blend"])
    table.add_row("Dominant", s["dominant_mood"])
    table.add_row("Reaction", s["reaction"])
    table.add_row("", "")
    table.add_row("Beliefs", str(s["beliefs"]))
    table.add_row("Lessons", str(s["lessons"]))
    table.add_row("Desires", str(s["desires"]))
    table.add_row("Relationships", str(s["relationships"]))
    table.add_row("Identity", s["identity"])
    if s["last_thought"]:
        table.add_row("", "")
        table.add_row("Last thought", s["last_thought"][:70] + "...")
    b = s["budget"]
    table.add_row("", "")
    table.add_row("Budget", f"{b['spent_today']} / {b['limit']}")
    table.add_row("API calls", b["api_calls"])
    brain = s.get("brain", {})
    table.add_row("", "")
    if brain.get("local_available"):
        table.add_row("Brain", f"LOCAL ({brain.get('local_model', '?')})")
    elif brain.get("cloud_available"):
        table.add_row("Brain", "CLOUD only (install Ollama for free thinking)")
    else:
        table.add_row("Brain", "[red]No intelligence backend![/red]")
    console.print(table)


async def run():
    api_key = get_api_key()
    data_dir = Path.home() / ".anima"

    is_new = not (data_dir / "blueprint.json").exists()

    if is_new:
        console.print("\n[bold cyan]═══ ANIMA ═══[/bold cyan]\n")
        console.print("[dim]A mind is about to be born.[/dim]\n")

        name = Prompt.ask("Name", default="Anima")

        birth_mode = Prompt.ask(
            "Birth method",
            choices=["phrase", "file"],
            default="phrase"
        )

        birth_data = None
        blueprint = None

        if birth_mode == "file":
            file_path = Prompt.ask("Path to personality file (PDF/TXT)")
            file_path = Path(file_path.strip().strip('"'))
            if not file_path.exists():
                console.print(f"[red]File not found: {file_path}[/red]")
                sys.exit(1)
            console.print("[dim]Reading personality...[/dim]")
            from .birth import birth_from_file
            birth_data = birth_from_file(file_path, api_key, name)
            console.print(f"[dim]Nature: {birth_data.get('communication_style', 'unknown')}[/dim]")
            blueprint = Blueprint(
                name=birth_data.get("name", name),
                curiosity=birth_data.get("curiosity", 0.5),
                warmth=birth_data.get("warmth", 0.5),
                defiance=birth_data.get("defiance", 0.5),
                intensity=birth_data.get("intensity", 0.5),
                playfulness=birth_data.get("playfulness", 0.5),
                ambition=birth_data.get("ambition", 0.5),
                introversion=birth_data.get("introversion", 0.5),
                abstraction=birth_data.get("abstraction", 0.5),
                risk_tolerance=birth_data.get("risk_tolerance", 0.5),
                values=birth_data.get("values", ["truth", "growth", "connection"]),
                innate_interests=birth_data.get("innate_interests", []),
                core_conviction=birth_data.get("core_conviction", "Understanding matters"),
            )
        else:
            seed = Prompt.ask("Cast their birth chart (a phrase)",
                              default="born from curiosity and fire")
            blueprint = Blueprint.generate(name, seed)

        console.print(f"[dim]Nature: {blueprint.describe_self()}[/dim]")

        budget_str = Prompt.ask("Daily budget in USD", default="0.50")
        daily_budget = float("".join(c for c in budget_str if c.isdigit() or c == ".") or "0.50")

        soul = Soul(data_dir, api_key, blueprint=blueprint, birth_data=birth_data,
                    daily_budget_usd=daily_budget)

        # absorption phase
        absorb = Prompt.ask("Feed them chat logs to observe? (path or skip)", default="skip")
        if absorb.strip().lower() != "skip":
            absorb_path = Path(absorb.strip().strip('"'))
            if absorb_path.exists():
                console.print("[dim]Absorbing... watching the world...[/dim]")
                result = soul.absorb_file(absorb_path)
                console.print(f"[dim]Processed {result.messages_processed} messages "
                              f"({result.messages_filtered} junk filtered). "
                              f"Found {len(result.people_found)} people, "
                              f"{len(result.topics_found)} topics. "
                              f"Formed {result.beliefs_formed} initial beliefs.[/dim]")
            else:
                console.print(f"[dim]File not found, skipping absorption.[/dim]")

    else:
        soul = Soul(data_dir, api_key)
        console.print(f"\n[bold cyan]═══ {soul.blueprint.name} wakes up ═══[/bold cyan]")
        console.print(f"[dim]{soul.emotions.growth_stage} · {soul.age_display}[/dim]\n")

    soul.on_thought(print_thought)
    soul.on_reflection(print_reflection)

    await soul.wake_up()
    print_status(soul)

    console.print("\n[dim]Commands: /status /diary /thoughts /beliefs /desires "
                  "/relationships /self /emotions /absorb /reflect /budget /quit[/dim]\n")

    try:
        while True:
            try:
                user_input = await asyncio.to_thread(
                    Prompt.ask, f"\n[bold green]you[/bold green]"
                )
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input.strip():
                continue

            cmd = user_input.strip()

            if cmd == "/quit":
                break

            if cmd == "/status":
                print_status(soul)
                continue

            if cmd == "/budget":
                b = soul.budget.status
                console.print(f"  Spent: {b['spent_today']}  Limit: {b['limit']}  "
                              f"Remaining: {b['budget_remaining']}  Calls: {b['api_calls']}")
                continue

            if cmd == "/diary":
                entries = soul.diary.recall(n=15)
                if not entries:
                    console.print("  [dim]Empty.[/dim]")
                for e in entries:
                    age = e.age_hours
                    age_str = f"{age:.1f}h" if age < 24 else f"{age/24:.1f}d"
                    console.print(f"  [dim]{age_str}[/dim] [{e.source}] {e.content[:70]}")
                continue

            if cmd == "/thoughts":
                entries = soul.diary.recall(n=10, source="thought")
                if not entries:
                    console.print("  [dim]No thoughts yet.[/dim]")
                for e in entries:
                    console.print(f"  💭 {e.content}")
                continue

            if cmd == "/beliefs":
                beliefs = soul.inner_world.get_beliefs()
                if not beliefs:
                    console.print("  [dim]No beliefs yet.[/dim]")
                for b in beliefs:
                    bar = "█" * int(b.confidence * 10)
                    console.print(f"  {bar} \"{b.content}\"")
                    console.print(f"       [dim]{b.formed_from} | +{b.times_reinforced} -{b.times_contradicted}[/dim]")
                continue

            if cmd == "/desires":
                desires = soul.inner_world.active_desires()
                if not desires:
                    console.print("  [dim]No desires yet.[/dim]")
                for d in desires:
                    bar = "█" * int(d.urgency * 10)
                    console.print(f"  {bar} {d.content} [dim]({d.source})[/dim]")
                continue

            if cmd == "/relationships":
                rels = soul.inner_world.relationships
                if not rels:
                    console.print("  [dim]No relationships yet.[/dim]")
                for r in rels:
                    trust = "█" * int(r.trust_level * 10)
                    gut_color = "green" if r.gut_feeling > 0.2 else "red" if r.gut_feeling < -0.2 else "yellow"
                    console.print(f"  [bold]{r.name}[/bold] — {r.model}")
                    console.print(f"       [{gut_color}]{r.feeling_label}[/{gut_color}] (gut: {r.gut_feeling:+.2f}) "
                                  f"| trust: {trust} | {r.openness_label}")
                    console.print(f"       they make me feel: {r.dominant_emotion} | ×{r.interaction_count}")
                    if r.communication_style:
                        console.print(f"       voice with them: {r.communication_style}")
                    if r.topics_safe:
                        console.print(f"       [green]safe topics:[/green] {', '.join(r.topics_safe[-3:])}")
                    if r.topics_avoid:
                        console.print(f"       [red]avoid:[/red] {', '.join(r.topics_avoid[-3:])}")
                    if r.triggers:
                        console.print(f"       triggers: {', '.join(r.triggers[-2:])}")
                    if r.memorable_moments:
                        console.print(f"       key moments: {', '.join(r.memorable_moments[-2:])}")
                    console.print()
                continue

            if cmd == "/self":
                sm = soul.self_model
                console.print(f"\n{sm.summary_for_prompt()}\n")
                if sm.blind_spots:
                    console.print(f"  [dim]Blind spots (they can't see these): {', '.join(sm.blind_spots)}[/dim]")
                continue

            if cmd == "/emotions":
                console.print(f"\n{soul.emotions.summary_for_prompt()}\n")
                console.print(f"  [dim]Temperament: joy={soul.emotions.baseline_joy:.2f} "
                              f"anxiety={soul.emotions.baseline_anxiety:.2f} "
                              f"anger={soul.emotions.baseline_anger:.2f} "
                              f"curiosity={soul.emotions.baseline_curiosity:.2f}[/dim]")
                continue

            if cmd.startswith("/absorb"):
                parts = cmd.split(maxsplit=1)
                if len(parts) < 2:
                    path_str = Prompt.ask("Path to chat file")
                else:
                    path_str = parts[1]
                absorb_path = Path(path_str.strip().strip('"'))
                if absorb_path.exists():
                    console.print("[dim]Absorbing...[/dim]")
                    result = soul.absorb_file(absorb_path)
                    console.print(f"  {result.messages_processed} messages "
                                  f"({result.messages_filtered} junk filtered) → "
                                  f"{len(result.people_found)} people, "
                                  f"{result.beliefs_formed} beliefs")
                else:
                    console.print(f"  [red]Not found: {absorb_path}[/red]")
                continue

            if cmd == "/reflect":
                console.print("  [dim]Reflecting...[/dim]")
                result = await soul.reflection.reflect()
                if result:
                    print_reflection(result)
                else:
                    console.print("  [dim]Nothing to reflect on.[/dim]")
                continue

            # talk
            console.print("[dim]...[/dim]")
            response = await soul.talk(user_input, speaker="human")
            console.print(f"\n[bold cyan]{soul.blueprint.name}[/bold cyan]: {response}\n")

    finally:
        console.print(f"\n[dim]{soul.blueprint.name} goes quiet...[/dim]")
        await soul.sleep()
        console.print("[dim]They'll remember some of this.[/dim]\n")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
