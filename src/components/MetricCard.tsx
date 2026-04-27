import type React from "react";
import { shortNumber } from "../utils";

type MetricCardProps = {
  label: string;
  value: number;
  hint: string;
  icon: React.ReactNode;
  tone?: "green" | "blue" | "amber" | "violet";
};

export function MetricCard({ label, value, hint, icon, tone = "green" }: MetricCardProps) {
  return (
    <article className={`metricCard ${tone}`}>
      <div className="metricIcon">{icon}</div>
      <p>{label}</p>
      <strong>
        {shortNumber(value)}
        {label.includes("可信") ? "%" : ""}
      </strong>
      <span className="metricHint">{hint}</span>
    </article>
  );
}
