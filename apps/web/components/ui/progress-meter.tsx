export interface ProgressMeterProps {
  value: number;
  max: number;
  label: string;
  showValue?: boolean;
}

export function ProgressMeter({ value, max, label, showValue = true }: ProgressMeterProps) {
  const safeMax = max > 0 ? max : 1;
  const percentage = Math.min(100, Math.max(0, (value / safeMax) * 100));
  const valueLabel = `${Math.round(percentage)}%`;

  return (
    <div className="progress-meter" aria-label={label}>
      <div className="progress-meter-heading">
        <span>{label}</span>
        {showValue ? <span>{valueLabel}</span> : null}
      </div>
      <div className="progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
        <span style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}
