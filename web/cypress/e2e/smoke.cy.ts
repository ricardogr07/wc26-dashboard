// Smoke tests use cy.intercept to stub API calls so they run without a live backend.

describe("App smoke", () => {
  beforeEach(() => {
    cy.intercept("GET", "/api/standings", { fixture: "standings.json" }).as("standings");
    cy.intercept("GET", "/api/matches*", { fixture: "matches.json" }).as("matches");
    cy.intercept("POST", "/api/simulate", { fixture: "simulation.json" }).as("simulate");
  });

  it("standings page loads with participant data", () => {
    cy.visit("/");
    cy.wait("@standings");
    cy.get("h1").should("contain", "Standings");
    cy.get("table").should("exist");
    cy.contains("Ricardo").should("exist");
  });

  it("schedule page loads and displays matches", () => {
    cy.visit("/schedule/");
    cy.wait("@matches");
    cy.get("h1").should("contain", "Schedule");
    cy.contains("United States").should("exist");
  });

  it("simulation page loads probabilities", () => {
    cy.visit("/simulate/");
    cy.wait("@simulate");
    cy.get("h1").should("contain", "Simulation");
    cy.get("table").should("exist");
  });

  it("scenario builder runs and shows probability deltas", () => {
    // Register scenario intercept first (lower priority), then baseline (times: 1, higher priority).
    // Cypress uses LIFO ordering, so the last-registered intercept matches first.
    // First POST → baseline (simulation.json, consumed after 1 use).
    // Second POST → scenario (simulation-scenario.json).
    cy.intercept("POST", "/api/simulate", { fixture: "simulation-scenario.json" }).as(
      "simulateScenario"
    );
    cy.intercept({ method: "POST", url: "/api/simulate", times: 1 }, { fixture: "simulation.json" }).as(
      "simulateBaseline"
    );

    cy.visit("/simulate/");
    cy.wait("@simulateBaseline");
    cy.wait("@matches");

    // Select "Home" wins for the first match
    cy.contains("button", "Home").first().click();

    // Run Scenario button appears at the bottom of the card — click it
    cy.contains("button", "Run Scenario").click();
    cy.wait("@simulateScenario");

    // Scenario results section should appear
    cy.get("[data-cy=scenario-results-heading]").should("exist");

    // At least one probability delta badge (e.g. +8.0pp) should be visible
    cy.contains(/[+-]\d+\.\dpp/).should("exist");
  });
});
