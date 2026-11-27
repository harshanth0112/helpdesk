import React, { useEffect, useState } from 'react';

/**
 * Optional difference-blend cursor for desktop devices with a fine pointer.
 * Adheres strictly to ui.md Section 7:
 * - Disabled on touch devices and if prefers-reduced-motion is true.
 * - Scales smoothly over interactive elements.
 */
export const CustomCursor = () => {
  const [position, setPosition] = useState({ x: -100, y: -100 });
  const [isHovered, setIsHovered] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Check for fine pointer (mouse) and no reduced motion preference
    const hasFinePointer = window.matchMedia('(pointer: fine)').matches;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!hasFinePointer || prefersReducedMotion) return;

    const handleMouseMove = (e) => {
      setIsVisible(true);
      setPosition({ x: e.clientX, y: e.clientY });

      const target = e.target;
      if (
        target.closest('button') ||
        target.closest('a') ||
        target.closest('input') ||
        target.closest('select') ||
        target.closest('textarea') ||
        target.closest('[role="button"]')
      ) {
        setIsHovered(true);
      } else {
        setIsHovered(false);
      }
    };

    const handleMouseLeave = () => setIsVisible(false);

    window.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  if (!isVisible) return null;

  return (
    <div
      className="fixed pointer-events-none z-50 rounded-full bg-white mix-blend-difference transition-transform duration-150 ease-out"
      style={{
        width: '28px',
        height: '28px',
        left: `${position.x - 14}px`,
        top: `${position.y - 14}px`,
        transform: isHovered ? 'scale(2.2)' : 'scale(1)',
      }}
    />
  );
};
