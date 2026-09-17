// react-cytoscapejs ships no TypeScript types (and none exist on
// DefinitelyTyped) — a minimal shim covering only what this project uses.
declare module "react-cytoscapejs" {
  import type { Core, ElementDefinition, LayoutOptions, Stylesheet } from "cytoscape";
  import type { Component } from "react";

  export interface CytoscapeComponentProps {
    elements: ElementDefinition[];
    layout?: LayoutOptions;
    stylesheet?: Stylesheet[];
    style?: React.CSSProperties;
    className?: string;
    cy?: (cy: Core) => void;
  }

  export default class CytoscapeComponent extends Component<CytoscapeComponentProps> {}
}
