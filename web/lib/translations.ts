export type Locale = "en" | "es";

type Translations = {
  nav: { standings: string; schedule: string; teams: string; simulation: string };
  standings: {
    title: string;
    subtitle: string;
    rank: string;
    participant: string;
    score: string;
    teams: string;
    loading: string;
    error: string;
    scoring: string;
  };
  scoringMilestones: {
    groupQualification: string;
    round32win: string;
    round16win: string;
    quarterfinalWin: string;
    semifinalWin: string;
    championshipWin: string;
  };
  simulate: {
    title: string;
    subtitle: string;
    lastRun: string;
    simulations: string;
    matchesCompleted: string;
    participant: string;
    scenarioBuilderTitle: string;
    scenarioBuilderDesc: string;
    loading: string;
    error: string;
  };
  schedule: {
    title: string;
    subtitle: string;
    loading: string;
    error: string;
    allRounds: string;
    noMatches: string;
  };
  teams: {
    title: string;
    subtitle: string;
    loading: string;
    error: string;
    sortByScore: string;
    sortByParticipant: string;
    sortByName: string;
    noTeamsFilter: string;
    pts: string;
    statusAll: string;
  };
  rounds: { group: string; r32: string; r16: string; qf: string; sf: string; final: string };
  status: {
    active: string;
    eliminated: string;
    champion: string;
    qualified: string;
    scheduled: string;
    live: string;
    completed: string;
  };
  positions: { "1st": string; "2nd": string; "3rd": string; "4th": string; "5th": string };
};

const en: Translations = {
  nav: {
    standings: "Standings",
    schedule: "Schedule",
    teams: "Teams",
    simulation: "Simulation",
  },
  standings: {
    title: "Standings",
    subtitle: "Rankings based on tournament milestones reached by each participant's teams.",
    rank: "RANK",
    participant: "PARTICIPANT",
    score: "SCORE",
    teams: "TEAMS",
    loading: "Loading standings…",
    error: "Failed to load standings.",
    scoring: "Scoring",
  },
  scoringMilestones: {
    groupQualification: "Group qualification",
    round32win: "Round of 32 win",
    round16win: "Round of 16 win",
    quarterfinalWin: "Quarterfinal win",
    semifinalWin: "Semifinal win",
    championshipWin: "Championship win",
  },
  simulate: {
    title: "Simulation",
    subtitle: "Monte Carlo win probability by final position for each participant.",
    lastRun: "Last run:",
    simulations: "simulations",
    matchesCompleted: "matches completed",
    participant: "PARTICIPANT",
    scenarioBuilderTitle: "Scenario Builder",
    scenarioBuilderDesc:
      "Coming in a future update — select hypothetical winners and see how probabilities shift.",
    loading: "Loading simulation…",
    error: "Failed to load simulation.",
  },
  schedule: {
    title: "Schedule",
    subtitle: "Match schedule with participant team highlights.",
    loading: "Loading schedule…",
    error: "Failed to load schedule.",
    allRounds: "All Rounds",
    noMatches: "No matches found for this filter.",
  },
  teams: {
    title: "Teams",
    subtitle: "Team ownership and tournament status by participant.",
    loading: "Loading teams…",
    error: "Failed to load teams.",
    sortByScore: "Sort by Score",
    sortByParticipant: "Sort by Participant",
    sortByName: "Sort by Name",
    noTeamsFilter: "No teams match this filter.",
    pts: "pts",
    statusAll: "All",
  },
  rounds: {
    group: "Group Stage",
    r32: "Round of 32",
    r16: "Round of 16",
    qf: "Quarterfinal",
    sf: "Semifinal",
    final: "Final",
  },
  status: {
    active: "Active",
    eliminated: "Eliminated",
    champion: "Champion",
    qualified: "Qualified",
    scheduled: "Scheduled",
    live: "Live",
    completed: "FT",
  },
  positions: { "1st": "1st", "2nd": "2nd", "3rd": "3rd", "4th": "4th", "5th": "5th" },
};

const es: Translations = {
  nav: {
    standings: "Clasificación",
    schedule: "Calendario",
    teams: "Equipos",
    simulation: "Simulación",
  },
  standings: {
    title: "Clasificación",
    subtitle:
      "Clasificación basada en los hitos del torneo alcanzados por los equipos de cada participante.",
    rank: "POS.",
    participant: "PARTICIPANTE",
    score: "PUNTOS",
    teams: "EQUIPOS",
    loading: "Cargando clasificación…",
    error: "Error al cargar la clasificación.",
    scoring: "Puntuación",
  },
  scoringMilestones: {
    groupQualification: "Clasificación de grupo",
    round32win: "Victoria en octavos",
    round16win: "Victoria en dieciseisavos",
    quarterfinalWin: "Victoria en cuartos de final",
    semifinalWin: "Victoria en semifinales",
    championshipWin: "Victoria en la final",
  },
  simulate: {
    title: "Simulación",
    subtitle:
      "Probabilidad de ganar por posición final por participante (Monte Carlo).",
    lastRun: "Última ejecución:",
    simulations: "simulaciones",
    matchesCompleted: "partidos completados",
    participant: "PARTICIPANTE",
    scenarioBuilderTitle: "Constructor de Escenarios",
    scenarioBuilderDesc:
      "Disponible en una futura actualización — elige ganadores hipotéticos y observa cómo cambian las probabilidades.",
    loading: "Cargando simulación…",
    error: "Error al cargar la simulación.",
  },
  schedule: {
    title: "Calendario",
    subtitle: "Calendario de partidos con destaque de equipos de cada participante.",
    loading: "Cargando calendario…",
    error: "Error al cargar el calendario.",
    allRounds: "Todas las Rondas",
    noMatches: "No se encontraron partidos para este filtro.",
  },
  teams: {
    title: "Equipos",
    subtitle: "Propietario y estado en el torneo por participante.",
    loading: "Cargando equipos…",
    error: "Error al cargar los equipos.",
    sortByScore: "Ordenar por Puntos",
    sortByParticipant: "Ordenar por Participante",
    sortByName: "Ordenar por Nombre",
    noTeamsFilter: "Ningún equipo coincide con este filtro.",
    pts: "pts",
    statusAll: "Todos",
  },
  rounds: {
    group: "Fase de Grupos",
    r32: "Octavos de Final",
    r16: "Dieciseisavos",
    qf: "Cuartos de Final",
    sf: "Semifinales",
    final: "Final",
  },
  status: {
    active: "Activo",
    eliminated: "Eliminado",
    champion: "Campeón",
    qualified: "Clasificado",
    scheduled: "Programado",
    live: "En Vivo",
    completed: "FT",
  },
  positions: { "1st": "1°", "2nd": "2°", "3rd": "3°", "4th": "4°", "5th": "5°" },
};

export const translations: Record<Locale, Translations> = { en, es };
