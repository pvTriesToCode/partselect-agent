import React from "react";
import "./VideoCard.css";

function VideoCard({ metadata }) {
  if (!metadata || metadata.type !== "repair" || !metadata.video_thumbnail_url) return null;
  return (
    <div className="video-card">
      <a href={metadata.video_url} target="_blank" rel="noreferrer" className="video-card__link">
        <div className="video-card__thumb-container">
          <img src={metadata.video_thumbnail_url} alt="Repair video" className="video-card__thumb" />
          <div className="video-card__play">▶</div>
        </div>
        <div className="video-card__info">
          <div className="video-card__title">Watch: {metadata.symptom_matched} Repair Guide</div>
          <div className="video-card__sub">PartSelect Repair Video</div>
        </div>
      </a>
      {metadata.guide_url && (
        <a href={metadata.guide_url} target="_blank" rel="noreferrer" className="video-card__guide">
          Read full repair guide →
        </a>
      )}
    </div>
  );
}

export default VideoCard;
