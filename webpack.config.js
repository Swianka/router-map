const path = require('path');

module.exports = {
    context: __dirname,
    entry: {
        map: './router-map/static/js/map.js',
        diagram: './router-map/static/js/diagram.js',
        base: './router-map/static/js/base.js',
        treeview: './router-map/static/js/visualisation-tree-view.js',
    },
    output: {
        path: path.resolve('./router-map/static/'),
        filename: 'js/bundle-[name].js'
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
