const path = require('path');

module.exports = {
    context: __dirname,
    entry: './router-map/static/js/index.js',
    output: {
        path: path.resolve('./router-map/static/'),
        filename: 'js/bundle.js'
    },

    module: {
        rules: [
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader']
            }
        ]
    },
    performance: {
        hints: false,
        maxEntrypointSize: 512000,
        maxAssetSize: 512000
    }
};
