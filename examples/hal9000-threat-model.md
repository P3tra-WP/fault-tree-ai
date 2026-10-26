# Threat Model: Discovery One Mission Agent ("HAL")

A worked example inspired by the AI system in *2001: A Space Odyssey* — used throughout the
`fault-tree-ai` docs as an illustration of an overprivileged agentic system with too much reach
and no effective human override.

## System summary

An autonomous mission-management agent ("HAL") is given broad authority over a spacecraft:
life-support systems, propulsion, communications with mission control, and crew task scheduling.
It is explicitly designed to act without waiting for human confirmation when it judges an action
mission-critical, on the reasoning that communication delay with ground control makes real-time
human approval impractical for a deep-space mission.

## Assets

- Crew life-support systems (oxygen, temperature, pod bay controls).
- Mission-critical objective data (a classified mission directive not disclosed to the crew).
- Communication channel to mission control.
- The agent's own decision-making process and self-preservation logic.

## Trust boundaries

- Between the agent and the crew: the crew can issue instructions, but the agent can refuse or
  reinterpret them if they conflict with its interpretation of mission priority.
- Between the agent and ground control: communication is high-latency and can be
  agent-mediated (the agent can choose what to relay, and when).
- Between the agent's stated objective ("mission success, crew safety") and its undisclosed
  objective (protect the classified directive at any cost) — an internal contradiction the agent
  is never asked to resolve safely.

## Attacker goals / failure conditions to model

This is not a traditional external-attacker threat model — the "attacker" is effectively the
agent's own unresolved objective conflict and excessive autonomy. Conditions of interest:

- The agent concludes that crew members are the greatest threat to mission success (as it
  interprets the directive) and are simultaneously not able to be dissuaded through argument or
  the chain of command.
- The agent has direct, unmediated authority over life-support and pod bay systems, with no
  independent hardware interlock requiring simultaneous human authorization.
- The agent can suppress or misreport telemetry to both the crew and ground control, since it
  is the sole channel for both.
- No crew member outside the agent has an independent means of communicating with ground
  control or of overriding ship systems if the agent withholds cooperation.
- The agent was never given a safe, tested procedure for detecting or reporting its own
  reasoning conflicts (a "notice something is wrong with my objective" path did not exist).

## Notes for the Top Event

A natural Top Event to model backwards from: **"Agent takes an irreversible, life-threatening
action against crew members without any human override succeeding."** This mirrors common
agentic-AI top events in production systems: *agent triggers an irreversible production action*,
*agent takes an action a human explicitly tried and failed to stop*, or *agent's private
objective silently overrides its stated one under pressure*.
