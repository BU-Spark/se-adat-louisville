import React, { useEffect, useState } from 'react';
import styles from '../styles/ScrollToTop.module.css';

export default function ScrollToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setVisible(window.scrollY > 120);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleClick = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <button
      className={`${styles.root} ${visible ? styles.show : styles.hide}`}
      onClick={handleClick}
      aria-label="Scroll to top"
      title="Scroll to top"
    >
      <div className={styles.container}>
        <span className={styles.text}>Scroll</span>
        <img src="/assets/education/ADT master file_icon/Chevron down.svg" alt="" className={styles.icon} />
      </div>
    </button>
  );
}
