import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "quiet" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  wide?: boolean;
}

export function Button({ className = "", variant = "primary", wide = false, ...props }: ButtonProps) {
  return (
    <button
      className={`button button-${variant}${wide ? " button-wide" : ""}${className ? ` ${className}` : ""}`}
      {...props}
    />
  );
}

export type { ButtonVariant };
