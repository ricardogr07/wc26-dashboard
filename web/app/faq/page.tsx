"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useLocale } from "@/lib/locale-context";
import type { Locale } from "@/lib/translations";

// Long-form archive content lives here instead of translations.ts — it is
// page copy, not UI chrome.
const REPO_URL = "https://github.com/ricardogr07/wc26-dashboard";

const FAQ: Record<
  Locale,
  { title: string; subtitle: string; items: { q: string; a: React.ReactNode }[] }
> = {
  en: {
    title: "FAQ",
    subtitle: "What this was, how it worked, and how it was built.",
    items: [
      {
        q: "What is this site?",
        a: "A dashboard for a 5-person World Cup 2026 prediction pool (quiniela). Each participant owned 5 of the 48 national teams and earned points as their teams hit tournament milestones. During the tournament the site tracked live standings, the full match schedule, the knockout bracket, team ownership, and Monte Carlo win probabilities.",
      },
      {
        q: "Who won?",
        a: "Ricardo, with 46 points. His roster included Spain, who beat Argentina 1–0 in the final on July 19, 2026 — the championship win alone was worth 13 points. Final standings: Ricardo 46, Jaime 30, Chuy 20, Jibran 19, Arnoldo 7.",
      },
      {
        q: "How did the scoring work?",
        a: "Each team earned its owner points for every milestone it reached: 1 pt for qualifying from its group, 2 pts per Round-of-32 win, 3 pts per Round-of-16 win, 5 pts per quarterfinal win, 8 pts per semifinal win, and 13 pts for winning the final. A participant's score is the sum across their five teams.",
      },
      {
        q: "How was it built?",
        a: "Next.js + TypeScript + Tailwind CSS frontend hosted on Azure Static Web Apps; a Python 3.11 Azure Functions API; Azure Cosmos DB for storage; Terraform for the infrastructure; GitHub Actions for CI/CD (lint, unit tests, Cypress e2e, deploy).",
      },
      {
        q: "Where did the match data come from?",
        a: "A timer-triggered Azure Function synced scores and schedules from the TheSportsDB API throughout the tournament. Each completed match also updated the teams' Elo ratings, which fed the simulation.",
      },
      {
        q: "How did the win probabilities work?",
        a: "10,000 Monte Carlo simulations of the remaining tournament. Match outcomes were sampled from Elo-based win probabilities blended with a scikit-learn predictor; group-stage matches allowed draws, knockout rounds were winner-only, and each run credited the champion team's owner. A Scenario Builder let you pin hypothetical results and compare the shifted odds against the baseline.",
      },
      {
        q: "Is the site still live?",
        a: "It is now a static archive. After the final, the last API responses (standings, matches, simulation) were baked into the site as JSON snapshots and the Azure backend — Functions and Cosmos DB — was retired. Everything you see is the final state of the tournament, served as pure static files.",
      },
      {
        q: "Where is the source code?",
        a: (
          <>
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
              github.com/ricardogr07/wc26-dashboard
            </a>{" "}
            — MIT licensed.
          </>
        ),
      },
    ],
  },
  es: {
    title: "FAQ",
    subtitle: "Qué fue esto, cómo funcionaba y cómo se construyó.",
    items: [
      {
        q: "¿Qué es este sitio?",
        a: "El dashboard de una quiniela del Mundial 2026 entre 5 participantes. Cada uno era dueño de 5 de las 48 selecciones y ganaba puntos conforme sus equipos alcanzaban hitos del torneo. Durante el torneo, el sitio mostraba la clasificación en vivo, el calendario completo, la llave eliminatoria, la propiedad de equipos y probabilidades de ganar por Monte Carlo.",
      },
      {
        q: "¿Quién ganó?",
        a: "Ricardo, con 46 puntos. Su plantilla incluía a España, que venció 1–0 a Argentina en la final del 19 de julio de 2026 — solo la victoria en la final valía 13 puntos. Clasificación final: Ricardo 46, Jaime 30, Chuy 20, Jibran 19, Arnoldo 7.",
      },
      {
        q: "¿Cómo funcionaba la puntuación?",
        a: "Cada equipo daba puntos a su dueño por cada hito alcanzado: 1 pt por clasificar de su grupo, 2 pts por victoria en 16avos, 3 pts en octavos, 5 pts en cuartos, 8 pts en semifinales y 13 pts por ganar la final. El puntaje de un participante es la suma de sus cinco equipos.",
      },
      {
        q: "¿Cómo se construyó?",
        a: "Frontend en Next.js + TypeScript + Tailwind CSS alojado en Azure Static Web Apps; API en Azure Functions con Python 3.11; Azure Cosmos DB como base de datos; Terraform para la infraestructura; GitHub Actions para CI/CD (lint, pruebas unitarias, e2e con Cypress y despliegue).",
      },
      {
        q: "¿De dónde salían los datos de los partidos?",
        a: "Una Azure Function con timer sincronizaba marcadores y calendario desde la API de TheSportsDB durante todo el torneo. Cada partido completado también actualizaba el rating Elo de los equipos, que alimentaba la simulación.",
      },
      {
        q: "¿Cómo funcionaban las probabilidades?",
        a: "10,000 simulaciones Monte Carlo del resto del torneo. Los resultados se muestreaban con probabilidades basadas en Elo combinadas con un predictor de scikit-learn; la fase de grupos permitía empates, las eliminatorias solo tenían ganador y cada corrida acreditaba al dueño del equipo campeón. El Constructor de Escenarios permitía fijar resultados hipotéticos y comparar las probabilidades contra la línea base.",
      },
      {
        q: "¿El sitio sigue vivo?",
        a: "Ahora es un archivo estático. Tras la final, las últimas respuestas del API (clasificación, partidos y simulación) se integraron al sitio como snapshots JSON y el backend de Azure — Functions y Cosmos DB — se retiró. Todo lo que ves es el estado final del torneo, servido como archivos estáticos.",
      },
      {
        q: "¿Dónde está el código fuente?",
        a: (
          <>
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
              github.com/ricardogr07/wc26-dashboard
            </a>{" "}
            — licencia MIT.
          </>
        ),
      },
    ],
  },
};

export default function FaqPage() {
  const { locale } = useLocale();
  const { title, subtitle, items } = FAQ[locale];
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900" data-cy="faq-heading">
        {title}
      </h1>
      <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
      <div className="mt-6 rounded-lg border bg-white px-4 shadow-sm">
        <Accordion>
          {items.map((item, i) => (
            <AccordionItem key={i} value={`faq-${i}`}>
              <AccordionTrigger className="text-left text-sm font-semibold text-gray-700">
                {item.q}
              </AccordionTrigger>
              <AccordionContent>
                <p className="text-sm text-gray-600">{item.a}</p>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </div>
  );
}
