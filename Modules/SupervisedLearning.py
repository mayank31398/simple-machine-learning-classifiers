import numpy as np
from Modules.Density import FitDensityEstimate1D, PredictDensityEstimate1D
from Modules.Estimators import EMdD
from Modules.Metrics import Accuracy, roc_curve
from Modules.Distances import Distance
import matplotlib.pyplot as plt

class NaiveBayesClassifier:
    training_accuracy = 0
    mu = None
    sigma = None
    classes = None
    priors = None
    alphas = None
    algorithm = None
    
    def __init__(self, algorithm = "MLE"):
        self.algorithm = algorithm
    
    def Fit(self, x, y, num_alphas, iterations = 100, roc_plot = False, label = None):
#         x : (num_samples, num_features)
#         y : (num_samples)
        classes = list(set(y))
        
        num_samples = x.shape[0]

        self.priors, self.alphas, self.mu, self.sigma, posteriors = FitDensityEstimate1D(x, y, num_alphas, iterations, self.algorithm)

        temp = np.argmax(posteriors, axis = 1).reshape(num_samples, 1)
        classes = np.array(classes)
        
        if(roc_plot):
            ax = plt.subplot(1, 1, 1)

            if(label == None):
                for i in classes:
                    tpr, fpr, _ = roc_curve(y, np.max(posteriors, axis = 1), pos_label=i)
                    ax.plot(fpr, tpr, label = i)
                    handles, labels = ax.get_legend_handles_labels()
                    ax.legend(handles, labels)
            else:
                tpr, fpr, _ = roc_curve(y, np.max(posteriors, axis = 1), pos_label=label)
                ax.plot(fpr, tpr)
            
            plt.xlabel("False positive rate")
            plt.ylabel("True positive rate")
            plt.title("ROC curve")


        predictions = classes[temp]
        self.training_accuracy = Accuracy(predictions, y)
        self.classes = classes

        return predictions
    
    def Predict(self, x):
        classes = self.classes
        
        num_samples = x.shape[0]
        
        posteriors = PredictDensityEstimate1D(x, self.mu, self.sigma, self.classes, self.priors, self.alphas)
        
        temp = np.argmax(posteriors, axis = 1).reshape(num_samples, 1)
        classes = np.array(classes)

        predictions = classes[temp]
        
        return predictions

class BayesClassifier:
    training_accuracy = 0
    mu = None
    sigma = None
    classes = None
    priors = None
    alphas = None
    algorithm = None
    inverse = None
    
    def __init__(self, algorithm = "MLE", inverse = True):
        self.algorithm = algorithm
        self.inverse = inverse
    
    def Fit(self, x, y, num_alphas, iterations = 100):
        if(self.algorithm == "MLE"):
            iterations = 1
        epsilon = 1e-10
        
        classes = list(set(y))
        self.mu = {}
        self.sigma = {}
        self.alphas = {}
        priors = {}
        class_conditional = {}
        
        num_features = x.shape[1]
        num_samples = x.shape[0]

        z = 0
        for i in classes:
            temp = (y == i)
            priors[i] = x[temp].shape[0] / num_samples
            x_ = x[temp]
            
            alpha_, mu_, sigma_ = EMdD(x_, num_alphas[i], self.algorithm, iterations = iterations, inverse = self.inverse)
            self.mu[i] = mu_
            self.sigma[i] = sigma_
            self.alphas[i] = alpha_
            
            mu_ = mu_.reshape(num_alphas[i], num_features, 1)
            x_ = x.T
            x_ = x_.reshape(1, num_features, num_samples)

            gaussians_ = x_ - mu_
            gaussians_ = gaussians_.transpose([0, 2, 1])
            gaussians_ = np.matmul(gaussians_, np.linalg.inv(sigma_))
            gaussians_ = np.exp(-(gaussians_ * (x_ - mu_).transpose([0, 2, 1])).sum(axis = 2) / 2)
            gaussians_ /= (np.sqrt(np.linalg.det(sigma_).reshape(num_alphas[i], 1) + epsilon) * (2 * np.pi) ** (num_features / 2))
            gaussians_ = gaussians_.T
            
            gaussians_ *= alpha_
            gaussians_ = gaussians_.sum(axis = 1, keepdims = True)
            
            class_conditional[i] = gaussians_
            z += gaussians_ * priors[i]
        
        posteriors = class_conditional[classes[0]] * priors[classes[0]] / (z + epsilon)
        for i in range(1, len(classes)):
            i_ = classes[i]
            t = class_conditional[i_] * priors[i_] / (z + epsilon)
            posteriors = np.concatenate([posteriors, t], axis = 1)
            
        temp = np.argmax(posteriors, axis = 1).reshape(num_samples, 1)
        classes = np.array(classes)

        predictions = classes[temp]
        
        self.training_accuracy = Accuracy(predictions, y.reshape(num_samples, 1))
        self.classes = classes
        self.priors = priors
        
        return predictions
    
    def Predict(self, x):
        class_conditional = {}
        classes = self.classes
        priors = self.priors
        epsilon = 1e-10
        
        num_features = x.shape[1]
        num_samples = x.shape[0]

        z = 0
        for i in classes:
            mu_ = self.mu[i]
            sigma_ = self.sigma[i]
            alpha_ = self.alphas[i]
            num_alphas = alpha_.shape[1]
            
            mu_ = mu_.reshape(num_alphas, num_features, 1)
            x_ = x.T
            x_ = x_.reshape(1, num_features, num_samples)

            gaussians_ = x_ - mu_
            gaussians_ = gaussians_.transpose([0, 2, 1])
            gaussians_ = np.matmul(gaussians_, np.linalg.inv(sigma_))
            gaussians_ = np.exp(-(gaussians_ * (x_ - mu_).transpose([0, 2, 1])).sum(axis = 2) / 2)
            gaussians_ /= (np.sqrt(np.linalg.det(sigma_).reshape(num_alphas, 1) + epsilon) * (2 * np.pi) ** (num_features / 2))
            gaussians_ = gaussians_.T
            
            gaussians_ *= alpha_
            gaussians_ = gaussians_.sum(axis = 1, keepdims = True)
            
            class_conditional[i] = gaussians_
            z += gaussians_ * priors[i]
        
        posteriors = class_conditional[classes[0]] * priors[classes[0]] / (z + epsilon)
        for i in range(1, len(classes)):
            i_ = classes[i]
            t = class_conditional[i_] * priors[i_] / (z + epsilon)
            posteriors = np.concatenate([posteriors, t], axis = 1)
            
        temp = np.argmax(posteriors, axis = 1).reshape(num_samples, 1)
        classes = np.array(classes)

        predictions = classes[temp]
        
        return predictions

class kNNClassifier:
    distance_metric = None

    def __init__(self, distance_metric = "Euclidean"):
        self.distance_metric = distance_metric
    
    def Predict(self, x, y, x_test, k):
        num_samples = x.shape[0]
        num_features = x.shape[1]
        num_test_samples = x_test.shape[0]
            
        classes = list(set(y))
        
        try:
            x_ = x.T
            x_ = x_.reshape(1, num_features, num_samples)
            x_test_ = x_test.reshape(num_test_samples, num_features, 1)
            
            dist = Distance(x_, x_test_, metric = self.distance_metric, axis = 1)
            temp = np.argpartition(dist, k - 1, axis = 1)[:, :k].reshape(num_test_samples, k)
            # temp = np.argsort(dist, axis = 1)[:, :k].reshape(num_test_samples, k)
            
            temp = y[temp]
            predictions = []
            for i in range(num_test_samples):
                count = {}
                
                for j in classes:
                    count[j] = 0
                
                for j in range(k):
                    count[temp[i, j]] += 1
                
                prediction = classes[0]
                for j in range(1, len(classes)):
                    if(count[classes[j]] > count[prediction]):
                        prediction = classes[j]
                predictions.append(prediction)
            
            predictions = np.array(predictions)
            
            return predictions
        except:
            predictions = []

            for j in range(num_test_samples):
                nearest = []
                for i in range(num_samples):
                    nearest.append([Distance(x[i, :], x_test[j, :], metric = self.distance_metric), y[i]])
                
                nearest.sort(key = lambda x: x[0])
                
                count = {}
                for i in classes:
                    count[i] = 0
                
                for i in range(k):
                    count[nearest[i][1]] += 1
                
                prediction = classes[0]
                for i in range(1, len(classes)):
                    if(count[classes[i]] > count[prediction]):
                        prediction = classes[i]

                predictions.append(prediction)
            predictions = np.array(predictions)
            
            return predictions

class ParzenWindow:
    h = None
    x_train = None
    y_train = None
    classes = None
    kernel = None

    def __init__(self, h = 1, kernel = "Hypercube"):
        self.h = h
        self.kernel = kernel
    
    def Fit(self, x, y):
        self.x_train = x
        self.y_train = y
        self.classes = list(set(y))
    
    def Predict(self, x):
        if(self.kernel == "Hypercube"):
            num_test_samples = x.shape[0]
            classes = self.classes
            h = self.h
            
            predictions = []
            for i in range(num_test_samples):
                x_ = self.x_train - x[i, :]
                x_ = np.abs(x_).max(axis = 1)
                temp_ = x_ < h / 2
                
                temp_ = self.y_train[temp_]
                count = 0
                prediction = classes[0]
                for j in classes:
                    t_ = (temp_ == j).sum()
                    if(t_ > count):
                        count = t_
                        prediction = j
                
                predictions.append(prediction)
        elif(self.kernel == "Gaussian"):
            num_test_samples = x.shape[0]
            classes = self.classes
            h = self.h
            
            predictions = []
            for i in range(num_test_samples):
                x_ = self.x_train - x[i, :]
                x_ = np.exp(-(np.linalg.norm(x_, axis = 1) ** 2) / (2 * h ** 2))
                
                count = 0
                prediction = classes[0]
                for j in classes:
                    temp = self.y_train == j
                    temp = x_[temp]
                    t_ = temp.sum()
                    if(t_ > count):
                        count = t_
                        prediction = j

                predictions.append(prediction)
            
        return np.array(predictions)