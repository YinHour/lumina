const React = require('react');
const ReactDOMServer = require('react-dom/server');

// If we render a function named "search", what is the exact error string?
function search() {}
try {
  ReactDOMServer.renderToString(React.createElement('button', null, search));
} catch(e) {
  console.log(e.message);
}
