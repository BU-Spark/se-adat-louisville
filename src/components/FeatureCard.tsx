import { useState, type KeyboardEvent, type Key } from 'react';

interface FeatureCardProps {
  id: string;
  icon: string;
  title: string;
  description: string;
  details: string;
  key?: Key;
}

interface DetailSection {
  key: string;
  heading?: string;
  bullets: string[];
  paragraphs: string[];
}

export function FeatureCard({ id, icon, title, description, details }: FeatureCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleClick = () => {
    setIsExpanded(!isExpanded);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  const detailSections: DetailSection[] = details
    .split('\n\n')
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block, index): DetailSection | null => {
      const lines = block
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);

      if (lines.length === 0) {
        return null;
      }

      const [firstLine, ...remaining] = lines;
      const bulletLines = remaining.filter((line) => line.startsWith('•'));
      const paragraphLines = remaining.filter((line) => !line.startsWith('•')).map((line) => line.replace(/^•\s*/, ''));

      const hasBullets = bulletLines.length > 0;
      const section: DetailSection = {
        key: `${id}-section-${index}`,
        heading: hasBullets ? firstLine.replace(/:\s*$/, '') : undefined,
        bullets: hasBullets ? bulletLines.map((line) => line.replace(/^•\s*/, '')) : [],
        paragraphs: hasBullets ? paragraphLines : [firstLine, ...remaining].map((line) => line.replace(/^•\s*/, '')),
      };

      return section;
    })
    .filter((section): section is DetailSection => section !== null);

  return (
    <div
      className={`feature-card ${isExpanded ? 'expanded' : ''}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-expanded={isExpanded}
      aria-controls={`details-${id}`}
    >
      <div className="feature-icon">{icon}</div>
      <h2 className="feature-title">{title}</h2>
      <p className="feature-description">{description}</p>
      <div
        id={`details-${id}`}
        className={`feature-details ${isExpanded ? 'details-visible' : ''}`}
        aria-hidden={!isExpanded}
        data-testid="feature-details"
      >
        {detailSections.map((section) => (
          <div key={section.key} className="feature-details-section">
            {section.heading && <p className="feature-details-heading">{section.heading}</p>}
            {section.paragraphs.map((paragraph, paragraphIndex) => (
              <p key={`${section.key}-paragraph-${paragraphIndex}`} className="feature-details-paragraph">
                {paragraph}
              </p>
            ))}
            {section.bullets.length > 0 && (
              <ul className="feature-details-list">
                {section.bullets.map((item, itemIndex) => (
                  <li key={`${section.key}-bullet-${itemIndex}`}>{item}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
