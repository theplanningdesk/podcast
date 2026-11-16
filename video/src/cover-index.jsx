// Entry point for the Reel covers (render-cover.mjs): one still per Short or research clip.
import React from 'react';
import {Composition, registerRoot} from 'remotion';
import '@fontsource/arimo/400.css';
import '@fontsource/arimo/700.css';
import '@fontsource/lato/400.css';
import '@fontsource/lato/700.css';
import '@fontsource/lato/900.css';
import {Cover} from './Cover.jsx';

const Root = () => (
  <Composition id="Cover" component={Cover} width={1080} height={1920} fps={30} durationInFrames={1}
    defaultProps={{variant: 'daily', kicker: '', topic: '', title: '', show: 'The Planning Desk'}} />
);
registerRoot(Root);
