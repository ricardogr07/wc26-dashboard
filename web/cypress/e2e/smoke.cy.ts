// Per-page smoke tests. All API calls are intercepted — no live backend required.

function stubApis() {
  cy.intercept("GET", "/api/standings", { fixture: "standings.json" }).as("standings");
  cy.intercept("GET", "/api/matches*", { fixture: "matches.json" }).as("matches");
  cy.intercept("POST", "/api/simulate", { fixture: "simulation.json" }).as("simulate");
}

// ── Navigation ──────────────────────────────────────────────────────────────

describe("Navigation", () => {
  beforeEach(stubApis);

  it("nav contains links for all five pages", () => {
    cy.viewport(1280, 800);
    cy.visit("/");
    cy.get("nav").within(() => {
      cy.contains("a", "Standings").should("exist");
      cy.contains("a", "Schedule").should("exist");
      cy.contains("a", "Bracket").should("exist");
      cy.contains("a", "Teams").should("exist");
      cy.contains("a", "Simulation").should("exist");
    });
  });
});

// ── Standings (/) ────────────────────────────────────────────────────────────

describe("Standings page (/)", () => {
  beforeEach(stubApis);

  it("shows heading and table", () => {
    cy.viewport(1280, 800);
    cy.visit("/");
    cy.wait("@standings");
    cy.get("[data-cy=standings-heading]").should("contain.text", "Standings");
    cy.get("[data-cy=standings-table]").should("exist");
  });

  it("lists all participants", () => {
    cy.visit("/");
    cy.wait("@standings");
    ["Ricardo", "Jibran", "Chuy", "Jaime", "Arnoldo"].forEach((name) => {
      cy.contains(name).should("exist");
    });
  });

  it("score column shows numbers", () => {
    cy.viewport(1280, 800);
    cy.visit("/");
    cy.wait("@standings");
    cy.get("[data-cy=standings-table]").within(() => {
      cy.contains(/^\d+$/).should("exist");
    });
  });

  it("shows error message when standings API fails", () => {
    cy.intercept("GET", "/api/standings", { statusCode: 500 }).as("standingsErr");
    cy.visit("/");
    cy.wait("@standingsErr");
    cy.contains("Failed to load standings").should("exist");
  });
});

// ── Schedule (/schedule) ─────────────────────────────────────────────────────

describe("Schedule page (/schedule)", () => {
  beforeEach(stubApis);

  it("shows heading and match cards", () => {
    cy.visit("/schedule/");
    cy.wait("@matches");
    cy.get("[data-cy=schedule-heading]").should("contain.text", "Schedule");
    cy.get("[data-cy=match-card]").should("have.length", 3);
  });

  it("regression: each match card shows a kick-off time on mobile", () => {
    cy.viewport("iphone-x");
    cy.visit("/schedule/");
    cy.wait("@matches");
    cy.get("[data-cy=match-card]").each(($card) => {
      cy.wrap($card).contains(/\d{1,2}:\d{2}/).should("exist");
    });
  });

  it("shows Live status badge for the in-progress match", () => {
    cy.visit("/schedule/");
    cy.wait("@matches");
    cy.get("[data-cy=status-badge]").contains(/live/i).should("exist");
  });

  it("shows FT status badge for the finished match", () => {
    cy.visit("/schedule/");
    cy.wait("@matches");
    cy.get("[data-cy=status-badge]").contains("FT").should("exist");
  });

  it("shows round filter bar on desktop", () => {
    cy.viewport(1280, 800);
    cy.visit("/schedule/");
    cy.wait("@matches");
    cy.get("[data-cy=round-filter]").should("be.visible");
  });

  it("shows error message when matches API fails", () => {
    cy.intercept("GET", "/api/matches*", { statusCode: 500 }).as("matchesErr");
    cy.visit("/schedule/");
    cy.wait("@matchesErr");
    cy.contains("Failed to load schedule").should("exist");
  });
});

// ── Simulate (/simulate) ─────────────────────────────────────────────────────

describe("Simulate page (/simulate)", () => {
  beforeEach(stubApis);

  it("shows heading and probability table", () => {
    cy.visit("/simulate/");
    cy.wait("@simulate");
    cy.get("[data-cy=simulate-heading]").should("contain.text", "Simulation");
    cy.get("[data-cy=prob-table]").should("exist");
  });

  it("regression: shows error message when simulate API returns 500", () => {
    cy.intercept("POST", "/api/simulate", { statusCode: 500 }).as("simulateErr");
    cy.visit("/simulate/");
    cy.wait("@simulateErr");
    cy.contains("Failed to load simulation").should("exist");
  });

  it("scenario builder runs and shows probability deltas", () => {
    // Cypress uses LIFO intercept ordering: last-registered wins.
    // Register fallback first (scenario), then baseline (consumed once) on top.
    cy.intercept("POST", "/api/simulate", { fixture: "simulation-scenario.json" }).as(
      "simulateScenario"
    );
    cy.intercept(
      { method: "POST", url: "/api/simulate", times: 1 },
      { fixture: "simulation.json" }
    ).as("simulateBaseline");

    cy.visit("/simulate/");
    cy.wait("@simulateBaseline");
    cy.wait("@matches");

    cy.contains("button", "Home").first().click();
    cy.contains("button", "Run Scenario").click();
    cy.wait("@simulateScenario");

    cy.get("[data-cy=scenario-results-heading]").should("exist");
    cy.contains(/[+-]\d+\.\dpp/).should("exist");
  });

  it("Reset button clears scenario selections", () => {
    cy.intercept("POST", "/api/simulate", { fixture: "simulation-scenario.json" }).as(
      "simulateScenario"
    );
    cy.intercept(
      { method: "POST", url: "/api/simulate", times: 1 },
      { fixture: "simulation.json" }
    ).as("simulateBaseline");

    cy.visit("/simulate/");
    cy.wait("@simulateBaseline");
    cy.wait("@matches");

    cy.contains("button", "Home").first().click();
    cy.contains("button", "Reset").click();
    cy.get("[data-cy=scenario-results-heading]").should("not.exist");
  });
});

// ── Bracket (/bracket) ───────────────────────────────────────────────────────

describe("Bracket page (/bracket)", () => {
  beforeEach(stubApis);

  it("shows heading and bracket tree", () => {
    cy.viewport(1280, 800);
    cy.visit("/bracket/");
    cy.wait("@matches");
    cy.get("[data-cy=bracket-heading]").should("contain.text", "Knockout Bracket");
    cy.get("[data-cy=bracket-tree]").should("exist");
  });

  it("shows 31 placeholder slots when no knockout matches are in the fixture", () => {
    // matches.json has only group-stage matches → all knockout slots are TBD
    cy.viewport(1280, 800);
    cy.visit("/bracket/");
    cy.wait("@matches");
    // 16 R32 + 8 R16 + 4 QF + 2 SF + 1 Final = 31 placeholders
    cy.get("[data-cy=bracket-placeholder]").should("have.length", 31);
    cy.get("[data-cy=bracket-match-card]").should("have.length", 0);
  });

  it("renders match cards when R32 data is present", () => {
    cy.intercept("GET", "/api/matches*", { fixture: "matches-bracket.json" }).as("bracketMatches");
    cy.viewport(1280, 800);
    cy.visit("/bracket/");
    cy.wait("@bracketMatches");
    cy.get("[data-cy=bracket-match-card]").should("have.length", 16);
    cy.get("[data-cy=bracket-placeholder]").should("have.length", 15);
  });

  it("highlights the winner of a completed match", () => {
    cy.intercept("GET", "/api/matches*", { fixture: "matches-bracket.json" }).as("bracketMatches");
    cy.viewport(1280, 800);
    cy.visit("/bracket/");
    cy.wait("@bracketMatches");
    // ARG beat KSA 3-0 in r32_01
    cy.get("[data-cy=bracket-match-card]")
      .first()
      .within(() => {
        cy.contains("Argentina").should("have.class", "bg-green-50");
      });
  });

  it("shows Live badge for an in-progress match", () => {
    cy.intercept("GET", "/api/matches*", { fixture: "matches-bracket.json" }).as("bracketMatches");
    cy.viewport(1280, 800);
    cy.visit("/bracket/");
    cy.wait("@bracketMatches");
    cy.get("[data-cy=bracket-match-card]").contains(/live/i).should("exist");
  });

  it("shows score for a completed match", () => {
    cy.intercept("GET", "/api/matches*", { fixture: "matches-bracket.json" }).as("bracketMatches");
    cy.viewport(1280, 800);
    cy.visit("/bracket/");
    cy.wait("@bracketMatches");
    cy.get("[data-cy=bracket-match-card]").contains("3–0").should("exist");
  });

  it("shows error message when matches API fails", () => {
    cy.intercept("GET", "/api/matches*", { statusCode: 500 }).as("matchesErr");
    cy.visit("/bracket/");
    cy.wait("@matchesErr");
    cy.contains("Failed to load bracket").should("exist");
  });
});

// ── Teams (/teams) ───────────────────────────────────────────────────────────

describe("Teams page (/teams)", () => {
  beforeEach(stubApis);

  it("shows heading and participant cards", () => {
    cy.viewport(1280, 800);
    cy.visit("/teams/");
    cy.wait("@standings");
    cy.get("[data-cy=teams-heading]").should("contain.text", "Teams");
    cy.get("[data-cy=participant-card]").should("have.length.gte", 1);
  });

  it("shows all 5 participant cards on desktop", () => {
    cy.viewport(1280, 800);
    cy.visit("/teams/");
    cy.wait("@standings");
    cy.get("[data-cy=participant-card]:visible").should("have.length", 5);
  });

  it("shows status badges for teams", () => {
    cy.viewport(1280, 800);
    cy.visit("/teams/");
    cy.wait("@standings");
    cy.get("[data-cy=status-badge]").should("have.length.gte", 1);
  });

  it("shows error message when standings API fails", () => {
    cy.intercept("GET", "/api/standings", { statusCode: 500 }).as("standingsErr");
    cy.visit("/teams/");
    cy.wait("@standingsErr");
    cy.contains("Failed to load teams").should("exist");
  });
});
