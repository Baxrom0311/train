import React from 'react';

interface LogoProps {
  className?: string;
  size?: number;
}

export const Logo: React.FC<LogoProps> = ({ className = '', size = 34 }) => {
  return (
    <div className={`relative flex items-center justify-center shrink-0 ${className}`} style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="transform transition-transform group-hover:scale-105 duration-300"
      >
        <defs>
          <linearGradient id="tjGradientPrimary" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#4F46E5" />
            <stop offset="50%" stopColor="#7C3AED" />
            <stop offset="100%" stopColor="#06B6D4" />
          </linearGradient>
          <linearGradient id="tjGradientGlow" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#A855F7" stopOpacity="0.8" />
          </linearGradient>
          <filter id="glowEffect" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Orqa fon yumaloq shakli */}
        <rect
          x="2"
          y="2"
          width="36"
          height="36"
          rx="11"
          fill="url(#tjGradientPrimary)"
          className="shadow-lg"
        />

        {/* Ichki nozik hoshiya */}
        <rect
          x="2.5"
          y="2.5"
          width="35"
          height="35"
          rx="10.5"
          stroke="white"
          strokeOpacity="0.25"
          strokeWidth="1"
        />

        {/* Futuristik Zamonaviy "T & J" Career Symbol */}
        <path
          d="M11 12H29C29.5523 12 30 12.4477 30 13V15.5C30 16.0523 29.5523 16.5 29 16.5H22V24.5C22 26.9853 19.9853 29 17.5 29C15.0147 29 13 26.9853 13 24.5V23C13 22.4477 13.4477 22 14 22H16.5C17.0523 22 17.5 22.4477 17.5 23V24.5C17.5 24.7761 17.7239 25 18 25C18.2761 25 18.5 24.7761 18.5 24.5V16.5H11C10.4477 16.5 10 16.0523 10 15.5V13C10 12.4477 10.4477 12 11 12Z"
          fill="white"
        />

        {/* Sparkle Accent */}
        <circle cx="27" cy="23" r="2.5" fill="#38BDF8" filter="url(#glowEffect)" />
        <circle cx="27" cy="23" r="1.5" fill="white" />
      </svg>
    </div>
  );
};


