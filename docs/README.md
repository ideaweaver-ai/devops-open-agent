# Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — DevOps Open Agent platform structure, shared components, and agent conventions

## Architecture diagrams (downloadable)

| File | Format | Description |
|------|--------|-------------|
| [architecture-diagram.html](./architecture-diagram.html) | HTML | Open in a browser; use Print → Save as PDF |
| [diagrams/system-context.png](./diagrams/system-context.png) | PNG | System context diagram |
| [diagrams/system-context.svg](./diagrams/system-context.svg) | SVG | System context (vector) |
| [diagrams/application-layers.png](./diagrams/application-layers.png) | PNG | Application layers diagram |
| [diagrams/application-layers.svg](./diagrams/application-layers.svg) | SVG | Application layers (vector) |
| [application-request-flow.canvas.tsx](./application-request-flow.canvas.tsx) | Canvas source | Application request flow only (matches interactive canvas) |
| [devops-open-agent-architecture.canvas.tsx](./devops-open-agent-architecture.canvas.tsx) | Canvas source | Full architecture canvas source |
| [devops-open-agent-architecture.html](./devops-open-agent-architecture.html) | HTML | Static export of application request flow — open in browser or Print → PDF |
| [diagrams/application-request-flow.svg](./diagrams/application-request-flow.svg) | SVG | Application request flow (vector) |
| [diagrams/application-request-flow.png](./diagrams/application-request-flow.png) | PNG | Application request flow |

**Interactive canvas in Cursor:** open the live canvas beside chat from
`~/.cursor/projects/Users-plakhera-open-devops-agent/canvases/devops-open-agent-architecture.canvas.tsx`.

**Regenerate PNG/SVG from Mermaid:**

```bash
cd docs/diagrams
npx @mermaid-js/mermaid-cli -i system-context.mmd -o system-context.png
npx @mermaid-js/mermaid-cli -i application-layers.mmd -o application-layers.png
```
