const path = require('path');

const config = {
  projectName: 'agri-miniapp',
  date: '2026-05-10',
  designWidth: 375,
  deviceRatio: {
    375: 2 / 1,
    640: 2.34 / 2,
    750: 1,
    828: 1.81 / 2,
    375: 2 / 1,
  },
  sourceRoot: 'src',
  outputRoot: 'dist',
  plugins: ['@tarojs/plugin-framework-react'],
  defineConstants: {},
  copy: {
    patterns: [
      { from: 'assets/', to: 'assets/' },
    ],
    options: {},
  },
  framework: 'react',
  compiler: {
    type: 'webpack5',
    prebundle: { enable: false },
  },
  mini: {
    webpackChain(chain) {
      // Copy static assets to dist
      const CopyPlugin = require('copy-webpack-plugin');
      chain.plugin('copy-assets').use(CopyPlugin, [{
        patterns: [
          { from: 'src/assets', to: 'assets', noErrorOnMissing: true },
        ],
      }]);
    },
    postcss: {
      pxtransform: {
        enable: true,
        config: {},
      },
      url: {
        enable: true,
        config: {
          limit: 1024,
        },
      },
      cssModules: {
        enable: false,
        config: {
          namingPattern: 'module',
          generateScopedName: '[name]__[local]___[hash:base64:5]',
        },
      },
    },
  },
  h5: {
    publicPath: './',
    staticDirectory: 'static',
    webpackChain(chain) {
      const CopyPlugin = require('copy-webpack-plugin');
      chain.plugin('copy-assets').use(CopyPlugin, [{
        patterns: [
          { from: 'src/assets', to: 'assets', noErrorOnMissing: true },
        ],
      }]);
    },
    postcss: {
      autoprefixer: {
        enable: true,
        config: {},
      },
      cssModules: {
        enable: false,
        config: {
          namingPattern: 'module',
          generateScopedName: '[name]__[local]___[hash:base64:5]',
        },
      },
    },
    devServer: {
      host: '0.0.0.0',
      port: 5173,
    },
  },
  alias: {
    '@': path.resolve(__dirname, '..', 'src'),
  },
};

module.exports = function (merge) {
  if (process.env.NODE_ENV === 'development') {
    return merge({}, config, require('./dev'));
  }
  return merge({}, config, require('./prod'));
};
