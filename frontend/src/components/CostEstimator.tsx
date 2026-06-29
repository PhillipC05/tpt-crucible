"use client";

interface CostBreakdown {
  component_cost: number;
  board_cost: number;
  assembly_cost: number;
  shipping_cost: number;
  node_count: number;
}

const sampleCost: CostBreakdown = {
  component_cost: 128.00,
  board_cost: 45.00,
  assembly_cost: 15.00,
  shipping_cost: 8.50,
  node_count: 16,
};

export function CostEstimator() {
  const total = sampleCost.component_cost + sampleCost.board_cost +
    sampleCost.assembly_cost + sampleCost.shipping_cost;
  const perNode = total / sampleCost.node_count;

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-amber mb-3">COST ESTIMATE</h3>
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-text-secondary">Components ({sampleCost.node_count} nodes)</span>
          <span>${sampleCost.component_cost.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">PCB Fabrication</span>
          <span>${sampleCost.board_cost.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Assembly</span>
          <span>${sampleCost.assembly_cost.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Shipping</span>
          <span>${sampleCost.shipping_cost.toFixed(2)}</span>
        </div>
        <div className="border-t border-border pt-2 flex justify-between font-bold">
          <span>Total</span>
          <span className="text-accent-amber">${total.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-text-secondary">
          <span>Per node</span>
          <span>${perNode.toFixed(2)}</span>
        </div>
      </div>
      <div className="mt-3 text-[10px] text-text-secondary">
        * Prices are estimates. Links to suppliers available on request.
      </div>
    </div>
  );
}
