// Smoke tests use cy.intercept to stub API calls so they run without a live backend.
// Phase 10 will add live-endpoint tests against the deployed SWA URL.

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
});
