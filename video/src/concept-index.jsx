// Entry point for the "Planning concept" clips (render-concept.mjs). Kept apart from index.jsx so
// episode renders never bundle the concept visuals and vice versa.
import React from 'react';
import {Composition, registerRoot} from 'remotion';
import '@fontsource/arimo/400.css';
import '@fontsource/arimo/700.css';
import '@fontsource/lato/400.css';
import '@fontsource/lato/700.css';
import '@fontsource/lato/900.css';
import {Story} from './concept/Frame.jsx';

const meta = ({props}) => ({durationInFrames: props.d?.total || 900});
const Root = () => (
  <>
    <Composition id="ConceptV" component={Story} width={1080} height={1920} fps={30} durationInFrames={900}
      defaultProps={{fmt: 'v', d: null}} calculateMetadata={meta} />
    <Composition id="ConceptP" component={Story} width={1080} height={1350} fps={30} durationInFrames={900}
      defaultProps={{fmt: 'p', d: null}} calculateMetadata={meta} />
  </>
);
registerRoot(Root);
