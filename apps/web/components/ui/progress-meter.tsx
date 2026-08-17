export interface ProgressMeterProps {
  value: number;
  max: number;
  percentage?: number;
  label: string;
  showValue?: boolean;
}

export function ProgressMeter({ value, max, percentage, label, showValue = true }: ProgressMeterProps) {
  const safeMax = max > 0 ? max : 1;
  const renderedPercentage = Math.min(100, Math.max(0, percentage ?? (value / safeMax) * 100));
  const valueLabel = `${Math.round(renderedPercentage)}%`;

  return (
    <div className="progress-meter" aria-label={label}>
      <div className="progress-meter-heading">
        <span>{label}</span>
        {showValue ? <span>{valueLabel}</span> : null}
      </div>
      <div className="progress-track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
        <span style={{ width: `${renderedPercentage}%` }} />
      </div>
    </div>
  );
}
